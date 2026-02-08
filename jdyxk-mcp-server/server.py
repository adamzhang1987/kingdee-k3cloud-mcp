import os
import json

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from k3cloud_webapi_sdk.main import K3CloudApiSdk

load_dotenv()

mcp = FastMCP("kingdee-k3cloud")

server_url = os.getenv("KD_SERVER_URL", "")
api_sdk = K3CloudApiSdk(server_url)
api_sdk.InitConfig(
    acct_id=os.getenv("KD_ACCT_ID", ""),
    user_name=os.getenv("KD_USERNAME", ""),
    app_id=os.getenv("KD_APP_ID", ""),
    app_secret=os.getenv("KD_APP_SEC", ""),
    server_url=server_url,
    lcid=int(os.getenv("KD_LCID", "2052")),
    org_num=int(os.getenv("KD_ORG_NUM", "0") or "0"),
)

SESSION_LOST_MSG = "会话信息已丢失，请重新登录"


def _is_session_lost(result_json: dict) -> bool:
    """判断金蝶返回是否为会话丢失错误。"""
    try:
        status = result_json.get("Result", {}).get("ResponseStatus", {})
        if not status.get("IsSuccess", True):
            for err in status.get("Errors") or []:
                if SESSION_LOST_MSG in (err.get("Message") or ""):
                    return True
    except (TypeError, AttributeError, KeyError):
        pass
    return False


def _call_with_session_retry(callable_fn):
    """执行一次 SDK 调用；若返回会话丢失则清空会话并重试一次。"""
    result = callable_fn()
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return result
    if not _is_session_lost(data):
        return result
    api_sdk.cookiesStore.SID = ""
    api_sdk.cookiesStore.cookies.clear()
    return callable_fn()


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
    return _call_with_session_retry(lambda: api_sdk.ExecuteBillQuery(
        {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": filter_string,
            "OrderString": order_string,
            "TopRowCount": top_count,
            "StartRow": start_row,
            "Limit": limit,
        }
    ))


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
    return _call_with_session_retry(lambda: api_sdk.BillQuery(
        {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": filter_string,
            "OrderString": order_string,
            "TopRowCount": top_count,
            "StartRow": start_row,
            "Limit": limit,
        }
    ))


@mcp.tool()
def view_bill(
    form_id: str,
    number: str = "",
    id: str = "",
) -> str:
    """查看金蝶云星空单条记录的完整详情。

    通过编号或内码查看单条记录的所有字段信息。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        number: 单据编号。如 "MATERIAL001"（number 和 id 二选一）
        id: 单据内码ID（number 和 id 二选一）
    """
    data = {"CreateOrgId": 0, "Number": number, "Id": id, "IsSortBySeq": "false"}
    return _call_with_session_retry(lambda: api_sdk.View(form_id, data))


@mcp.tool()
def save_bill(form_id: str, model_data: str) -> str:
    """保存金蝶云星空单据（新增或更新）。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        model_data: JSON格式的单据数据。示例（保存物料）：
            {"Model": {"FCreateOrgId": {"FNumber": "100"}, "FNumber": "MAT001", "FName": "物料名称"}}
            如果传入的JSON中没有"Model"键，会自动包装。
    """
    data = json.loads(model_data)
    if "Model" not in data:
        data = {"Model": data}
    return _call_with_session_retry(lambda: api_sdk.Save(form_id, data))


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
    data = {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
    }
    return _call_with_session_retry(lambda: api_sdk.Submit(form_id, data))


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
    data = {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
    }
    return _call_with_session_retry(lambda: api_sdk.Audit(form_id, data))


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
    data = {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
    }
    return _call_with_session_retry(lambda: api_sdk.UnAudit(form_id, data))


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
    data = {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
    }
    return _call_with_session_retry(lambda: api_sdk.Delete(form_id, data))


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
    data = {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
    }
    return _call_with_session_retry(lambda: api_sdk.ExcuteOperation(form_id, op_number, data))


if __name__ == "__main__":
    mcp.run()
