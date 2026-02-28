import os
import sys
import json

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from k3cloud_webapi_sdk.main import K3CloudApiSdk
from k3cloud_webapi_sdk.const.const_define import InvokeMethod

load_dotenv()

_required_env = ["KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"]
_missing_env = [k for k in _required_env if not os.getenv(k)]
if _missing_env:
    raise RuntimeError(f"Missing required env vars: {', '.join(_missing_env)}")

mcp = FastMCP("kingdee-k3cloud")

SESSION_LOST_MSG = "会话信息已丢失"


class RetryableK3CloudApiSdk(K3CloudApiSdk):
    """K3CloudApiSdk with automatic session recovery on expiry."""

    def Execute(self, service_name, json_data=None, invoke_type=InvokeMethod.SYNC):
        result = super().Execute(service_name, json_data, invoke_type)
        if isinstance(result, str) and SESSION_LOST_MSG in result:
            print("[k3cloud] session expired, resetting and retrying...", file=sys.stderr)
            self.cookiesStore.SID = ""
            self.cookiesStore.cookies.clear()
            result = super().Execute(service_name, json_data, invoke_type)
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


if __name__ == "__main__":
    mcp.run()
