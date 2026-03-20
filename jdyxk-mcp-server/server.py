import os
import sys
import json
import time

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings
from k3cloud_webapi_sdk.main import K3CloudApiSdk
from k3cloud_webapi_sdk.const.const_define import InvokeMethod
from k3cloud_webapi_sdk.model.cookie_store import CookieStore

load_dotenv()

_required_env = ["KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"]
_missing_env = [k for k in _required_env if not os.getenv(k)]
if _missing_env:
    raise RuntimeError(f"Missing required env vars: {', '.join(_missing_env)}")


class ApiKeyVerifier:
    """验证静态 API Key（Bearer Token）。

    仅在 SSE/streamable-http 传输时生效；MCP_API_KEY 未设置时禁用鉴权。
    """

    def __init__(self, api_key: str):
        self._key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        if token == self._key:
            return AccessToken(token=token, client_id="api-key-client", scopes=[])
        return None


_api_key = os.getenv("MCP_API_KEY", "")
_issuer_url = os.getenv("MCP_ISSUER_URL", "http://localhost:8000")
_token_verifier = ApiKeyVerifier(_api_key) if _api_key else None
_auth_settings = AuthSettings(issuer_url=_issuer_url, resource_server_url=_issuer_url) if _api_key else None

mcp = FastMCP("kingdee-k3cloud", token_verifier=_token_verifier, auth=_auth_settings)

SESSION_LOST_MSG = "会话信息已丢失"


def _check_expired(data) -> bool:
    if isinstance(data, list):
        return any(_check_expired(item) for item in data)
    if isinstance(data, dict):
        errors = (data.get("Result") or {}).get("ResponseStatus", {}).get("Errors", [])
        return any(SESSION_LOST_MSG in (e.get("Message") or "") for e in errors)
    return False


def _is_session_expired(result: str) -> bool:
    try:
        return _check_expired(json.loads(result))
    except Exception:
        return False


class RetryableK3CloudApiSdk(K3CloudApiSdk):
    """K3CloudApiSdk with automatic session recovery on expiry.

    When K3Cloud returns "会话信息已丢失", the recovery flow is:
      1. If the last session reset was more than _RESET_COOLDOWN seconds ago:
         clear cookiesStore so BuildHeader() sends no session headers on retry.
         The retry call lets the server issue a fresh SID (stored by
         FillCookieAndHeader), even though the response body still reports
         "session lost" while the new session activates server-side.
      2. If we reset recently (within cooldown), skip clearing — the freshly
         issued SID is preserved and retried directly.

    Rapid consecutive resets would destroy each newly-issued SID before it
    activates, so the 30-second cooldown keeps the latest SID intact until
    the server accepts it.
    """

    _RESET_COOLDOWN = 300  # seconds — new SID takes several minutes to activate server-side

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_reset_at = 0.0

    def Execute(self, service_name, json_data=None, invoke_type=InvokeMethod.SYNC):
        result = super().Execute(service_name, json_data, invoke_type)
        if isinstance(result, str) and _is_session_expired(result):
            now = time.monotonic()
            if now - self._session_reset_at >= self._RESET_COOLDOWN:
                # Reset: clear stale SID, make one fire-and-forget call so the server
                # issues a fresh SID (stored by FillCookieAndHeader). The response body
                # will still say "session lost" — discard it. Do NOT retry the original
                # request; return the error and let the SID activate over the next few
                # minutes. Subsequent calls will use the newly-stored SID.
                print("[k3cloud] session expired, re-establishing SID...", file=sys.stderr, flush=True)
                self._session_reset_at = now
                self.cookiesStore = CookieStore()
                super().Execute(service_name, json_data, invoke_type)  # establishes SID, result discarded
            else:
                # Within cooldown: a fresh SID was recently obtained. Do NOT retry —
                # retrying would cause the server to issue yet another new SID,
                # restarting the activation clock. Just return the error and wait.
                print("[k3cloud] session recovering, SID not yet active — skipping retry", file=sys.stderr, flush=True)
        return result


server_url = os.getenv("KD_SERVER_URL", "")
api_sdk = RetryableK3CloudApiSdk(server_url)
api_sdk.InitConfig(
    acct_id=os.getenv("KD_ACCT_ID", ""),
    user_name=os.getenv("KD_USERNAME", ""),
    app_id=os.getenv("KD_APP_ID", ""),
    app_secret=os.getenv("KD_APP_SEC", ""),
    server_url=server_url,
    lcid=int(os.getenv("KD_LCID", "2052")),
    org_num=int(os.getenv("KD_ORG_NUM", "0") or "0"),
)


def _ids_data(numbers: str, ids: str) -> dict:
    return {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": [i.strip() for i in ids.split(",") if i.strip()] if ids else [],
    }


@mcp.tool()
def query_bill(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    order_string: str = "",
    top_count: int = 100,
    start_row: int = 0,
    limit: int = 2000,
) -> str:
    """查询金蝶云星空单据数据（返回二维数组）。

    Args:
        form_id: 表单ID。常用值：
            BD_MATERIAL(物料)、BD_Customer(客户)、BD_Supplier(供应商)、
            SAL_SaleOrder(销售订单)、PUR_PurchaseOrder(采购订单)、
            STK_InStock(入库单)、STK_OutStock(出库单)、GL_VOUCHER(凭证)
        field_keys: 查询字段，逗号分隔。如 "FName,FNumber"
        filter_string: 过滤条件。如 "FNumber like 'MAT%'"
        order_string: 排序字段。如 "FNumber ASC"
        top_count: 返回最大行数，默认100
        start_row: 起始行号，默认0
        limit: 最大行数限制，默认2000
    """
    return api_sdk.ExecuteBillQuery(
        {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": filter_string,
            "OrderString": order_string,
            "TopRowCount": top_count,
            "StartRow": start_row,
            "Limit": limit,
        }
    )


@mcp.tool()
def query_bill_json(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    order_string: str = "",
    top_count: int = 100,
    start_row: int = 0,
    limit: int = 2000,
) -> str:
    """查询金蝶云星空单据数据（返回JSON格式，字段名作为key）。

    与 query_bill 的区别：返回结果是JSON对象数组，每条记录的字段名作为key，更易读。

    Args:
        form_id: 表单ID。常用值：
            BD_MATERIAL(物料)、BD_Customer(客户)、BD_Supplier(供应商)、
            SAL_SaleOrder(销售订单)、PUR_PurchaseOrder(采购订单)、
            STK_InStock(入库单)、STK_OutStock(出库单)、GL_VOUCHER(凭证)
        field_keys: 查询字段，逗号分隔。如 "FName,FNumber,FCreateOrgId,FUseOrgId"
        filter_string: 过滤条件。如 "FNumber like 'MAT%'"
        order_string: 排序字段。如 "FNumber ASC"
        top_count: 返回最大行数，默认100
        start_row: 起始行号，默认0
        limit: 最大行数限制，默认2000
    """
    return api_sdk.BillQuery(
        {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": filter_string,
            "OrderString": order_string,
            "TopRowCount": top_count,
            "StartRow": start_row,
            "Limit": limit,
        }
    )


@mcp.tool()
def view_bill(
    form_id: str,
    number: str = "",
    bill_id: str = "",
) -> str:
    """查看金蝶云星空单条记录的完整详情。

    通过编号或内码查看单条记录的所有字段信息。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        number: 单据编号。如 "MATERIAL001"（number 和 bill_id 二选一）
        bill_id: 单据内码ID（number 和 bill_id 二选一）
    """
    data = {"CreateOrgId": 0, "Number": number, "Id": bill_id, "IsSortBySeq": "false"}
    return api_sdk.View(form_id, data)


@mcp.tool()
def save_bill(form_id: str, model_data: str) -> str:
    """保存金蝶云星空单据（新增或更新）。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        model_data: JSON格式的单据数据。示例（保存物料）：
            {"Model": {"FCreateOrgId": {"FNumber": "100"}, "FNumber": "MAT001", "FName": "物料名称"}}
            如果传入的JSON中没有"Model"键，会自动包装。
    """
    try:
        data = json.loads(model_data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON in model_data: {e}"})
    if "Model" not in data:
        data = {"Model": data}
    return api_sdk.Save(form_id, data)


@mcp.tool()
def submit_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """提交金蝶云星空单据。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    return api_sdk.Submit(form_id, _ids_data(numbers, ids))


@mcp.tool()
def audit_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """审核金蝶云星空单据。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    return api_sdk.Audit(form_id, _ids_data(numbers, ids))


@mcp.tool()
def unaudit_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """反审核金蝶云星空单据。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    return api_sdk.UnAudit(form_id, _ids_data(numbers, ids))


@mcp.tool()
def delete_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """删除金蝶云星空单据。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    return api_sdk.Delete(form_id, _ids_data(numbers, ids))


@mcp.tool()
def execute_operation(
    form_id: str,
    op_number: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """执行金蝶云星空单据操作（禁用、反禁用等）。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        op_number: 操作类型。常用值：Forbid(禁用)、Enable(反禁用)
        numbers: 单据编号，多个用逗号分隔
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    return api_sdk.ExcuteOperation(form_id, op_number, _ids_data(numbers, ids))


@mcp.tool()
def query_metadata(form_id: str) -> str:
    """查询金蝶云星空表单的元数据（字段结构信息）。

    用于获取某个表单有哪些字段、字段类型等信息，便于构造查询和保存参数。

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
    """
    return api_sdk.QueryBusinessInfo({"FormId": form_id})


@mcp.tool()
def push_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
    rule_id: str = "",
    target_form_id: str = "",
    target_org_id: str = "0",
    target_bill_type_id: str = "",
    is_enable_default_rule: str = "true",
    custom_params: str = "",
) -> str:
    """下推金蝶云星空单据（如销售订单下推发货通知单）。

    Args:
        form_id: 源单表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder 等
        numbers: 源单编号，多个用逗号分隔。如 "XSDD000064,XSDD000065"
        ids: 源单内码ID，多个用逗号分隔（numbers 和 ids 二选一）
        rule_id: 转换规则ID。如 "SaleOrder-DeliveryNotice"（不填则用默认规则）
        target_form_id: 目标单据表单ID（不填则由规则决定）
        target_org_id: 目标组织ID，默认"0"
        target_bill_type_id: 目标单据类型ID（不填则用默认）
        is_enable_default_rule: 是否启用默认转换规则，默认"true"
        custom_params: 自定义参数JSON字符串。如 '{"FDATE":"2024-01-01"}'（不填则不传）
    """
    data = {
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
        "RuleId": rule_id,
        "TargetFormId": target_form_id,
        "TargetOrgId": target_org_id,
        "TargetBillTypeId": target_bill_type_id,
        "IsEnableDefaultRule": is_enable_default_rule,
    }
    if custom_params:
        try:
            data["CustomParams"] = json.loads(custom_params)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON in custom_params: {e}"})
    return api_sdk.Push(form_id, data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="传输协议（默认 stdio）",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
