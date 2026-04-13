import csv
import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from k3cloud_webapi_sdk.const.const_define import InvokeMethod
from k3cloud_webapi_sdk.main import K3CloudApiSdk
from k3cloud_webapi_sdk.model.cookie_store import CookieStore
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

SESSION_LOST_MSG = "会话信息已丢失"

# Write-tool guard: set to True in main() when --mode readonly is active.
# Write tools remain registered but return an error when this flag is set.
_readonly = False

# SDK instance: initialized in setup() after environment is validated.
api_sdk: "RetryableK3CloudApiSdk | None" = None


def _sdk() -> "RetryableK3CloudApiSdk":
    """Return the initialized SDK, asserting it is not None."""
    assert api_sdk is not None, "api_sdk not initialized — call setup() first"
    return api_sdk


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


mcp = FastMCP("kingdee-k3cloud")


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
    except (json.JSONDecodeError, TypeError, ValueError):
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
    activates, so the 300-second cooldown keeps the latest SID intact until
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
                logger.warning("[k3cloud] session expired, re-establishing SID...")
                self._session_reset_at = now
                if hasattr(self, "cookiesStore"):
                    self.cookiesStore = CookieStore()
                else:
                    logger.warning(
                        "[k3cloud] SDK internals changed: cookiesStore not found, cannot reset SID"
                    )
                super().Execute(
                    service_name, json_data, invoke_type
                )  # establishes SID, result discarded
            else:
                # Within cooldown: a fresh SID was recently obtained. Do NOT retry —
                # retrying would cause the server to issue yet another new SID,
                # restarting the activation clock. Just return the error and wait.
                logger.warning("[k3cloud] session recovering, SID not yet active — skipping retry")
        return result


def _ids_data(numbers: str, ids: str) -> dict:
    return {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": [i.strip() for i in ids.split(",") if i.strip()] if ids else [],
    }


def _wrap_query_result(raw: str, top_count: int, limit: int, start_row: int) -> str:
    """将 SDK 查询结果包装为带分页元数据的 envelope。

    仅对成功的列表响应生效；错误响应（如会话过期）原样透传。

    返回格式：
        {
          "rows": [...原始数据...],
          "row_count": N,
          "truncated": true/false,
          "next_start_row": N,   # 仅 truncated=true 时存在
          "hint": "..."          # 仅 truncated=true 时存在
        }
    """
    if _is_session_expired(raw):
        return raw

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    if not isinstance(data, list):
        return raw  # 非列表格式（如 API 错误对象）原样透传

    row_count = len(data)
    # 有效上限取 top_count 与 limit 的较小值（两者均为正时）
    cap = min(top_count, limit) if top_count > 0 and limit > 0 else top_count or limit

    truncated = row_count > 0 and row_count >= cap

    result: dict = {
        "rows": data,
        "row_count": row_count,
        "truncated": truncated,
    }
    if truncated:
        result["next_start_row"] = start_row + row_count
        result["hint"] = (
            f"返回行数已达上限（{cap} 行），数据可能被截断。"
            f"请用 start_row={start_row + row_count} 继续翻页，或缩小 filter_string 时间范围后重新查询。"
        )

    return json.dumps(result, ensure_ascii=False)


def _paginate_bill(
    params: dict, page_size: int, max_rows: int
) -> "tuple[list, bool, int, str | None]":
    """内部翻页原语。返回 (rows, exhausted, next_start_row, error_raw)。

    - rows: 已拉取的数据列表
    - exhausted=True 表示已拉完所有数据；False 表示因 max_rows 提前截断
    - next_start_row: 下次应从此行继续（exhausted=False 时有意义）
    - error_raw: 非 None 表示遇到 session expired / 格式错误，调用方应直接 return
    """
    rows: list = []
    initial_start = params.get("StartRow", 0)
    current_start = initial_start

    while True:
        page_params = {
            **params,
            "StartRow": current_start,
            "TopRowCount": page_size,
            "Limit": page_size,
        }
        raw = _sdk().BillQuery(page_params)

        if _is_session_expired(raw):
            return rows, False, current_start, raw

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return rows, False, current_start, raw

        if not isinstance(data, list):
            return rows, False, current_start, raw

        rows.extend(data)
        page_count = len(data)

        if len(rows) >= max_rows:
            rows = rows[:max_rows]
            return rows, False, initial_start + max_rows, None

        if page_count < page_size:
            return rows, True, initial_start + len(rows), None

        current_start += page_size


def _iter_date_chunks(date_from: str, date_to: str, chunk: str) -> "Iterator[tuple[str, str]]":
    """将 [date_from, date_to) 切成 N 个半开区间。chunk ∈ {'month','week','day'}。"""
    if chunk not in {"month", "week", "day"}:
        raise ValueError(f"chunk 必须是 month/week/day，收到: {chunk!r}")
    try:
        current = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
    except ValueError as e:
        raise ValueError(f"日期格式错误（需要 YYYY-MM-DD）: {e}") from e
    if end <= current:
        raise ValueError("date_to 必须晚于 date_from")

    while current < end:
        if chunk == "month":
            if current.month == 12:
                next_dt = date(current.year + 1, 1, 1)
            else:
                next_dt = date(current.year, current.month + 1, 1)
        elif chunk == "week":
            next_dt = current + timedelta(weeks=1)
        else:
            next_dt = current + timedelta(days=1)
        chunk_end = min(next_dt, end)
        yield current.isoformat(), chunk_end.isoformat()
        current = chunk_end


def _stream_to_file_handle(
    f,
    params: dict,
    page_size: int,
    max_rows: int,
    fields: list,
    fmt: str,
    header_written: bool,
) -> "tuple[int, bool, str | None]":
    """将分页查询结果流式追加写入已打开的文件句柄。

    Returns:
        (rows_written, header_written, error_raw)
        - rows_written: 本次写入的行数
        - header_written: CSV 表头是否已写（传入值或本次更新后的值）
        - error_raw: 非 None 表示遇到 session expired / 格式错误
    """
    writer = csv.writer(f) if fmt == "csv" else None
    rows_written = 0
    current_start = params.get("StartRow", 0)

    while True:
        page_params = {
            **params,
            "StartRow": current_start,
            "TopRowCount": page_size,
            "Limit": page_size,
        }
        raw = _sdk().BillQuery(page_params)

        if _is_session_expired(raw):
            return rows_written, header_written, raw

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return rows_written, header_written, raw

        if not isinstance(data, list):
            return rows_written, header_written, raw

        for row in data:
            if fmt == "ndjson":
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            elif writer is not None:  # fmt == "csv"
                if not header_written:
                    writer.writerow(fields)
                    header_written = True
                writer.writerow([row.get(field, "") for field in fields])
            rows_written += 1
            if rows_written >= max_rows:
                return rows_written, header_written, None

        if len(data) < page_size:
            break

        current_start += page_size

    return rows_written, header_written, None


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
    raw = _sdk().ExecuteBillQuery(
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
    return _wrap_query_result(raw, top_count, limit, start_row)


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
    raw = _sdk().BillQuery(
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
    return _wrap_query_result(raw, top_count, limit, start_row)


@mcp.tool()
def count_bill(form_id: str, filter_string: str = "") -> str:
    """估算某查询条件下的数据行数（不返回数据内容）。用于大数据量查询前的探测。

    返回 JSON 格式：
        {"estimated_rows": N, "is_exact": true/false, "hint": "..."}
    当 is_exact=false 时，实际行数 ≥ estimated_rows，建议按月/周分片查询。

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
        filter_string: 过滤条件。如 "FDate >= '2025-01-01' AND FDate < '2026-01-01'"
    """
    _PROBE_LIMIT = 5000
    raw = _sdk().BillQuery(
        {
            "FormId": form_id,
            "FieldKeys": "FID",
            "FilterString": filter_string,
            "TopRowCount": _PROBE_LIMIT,
            "StartRow": 0,
            "Limit": _PROBE_LIMIT,
        }
    )

    if _is_session_expired(raw):
        return raw

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    if not isinstance(data, list):
        return raw

    count = len(data)
    is_exact = count < _PROBE_LIMIT
    result: dict = {"estimated_rows": count, "is_exact": is_exact}
    if not is_exact:
        result["hint"] = (
            f"实际行数 ≥ {_PROBE_LIMIT}，建议按自然月分片查询（每月单独调用 query_bill_json）。"
        )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def query_bill_all(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    order_string: str = "",
    max_rows: int = 20000,
    page_size: int = 2000,
) -> str:
    """自动翻页查询直到拉完或达到 max_rows 安全上限。

    适合估算 ≤ 数千行的场景。大数据量（> 5000 行）请用 query_bill_to_file（落盘）
    或 query_bill_range（日期分片），避免超过 MCP 1 MB 返回限制。

    返回格式：
        {"rows": [...], "row_count": N, "exhausted": true/false,
         "next_start_row": N,   # 仅 exhausted=false 时
         "hint": "..."}         # 仅 exhausted=false 时

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
        field_keys: 查询字段，逗号分隔。如 "FBillNo,FDate,FAmount"
        filter_string: 过滤条件。如 "FDate >= '2025-01-01'"
        order_string: 排序字段。如 "FDate ASC"
        max_rows: 安全上限，默认 20000；超过则提前终止并返回 exhausted=false
        page_size: 每页行数，默认 2000，建议不超过 2000
    """
    params = {
        "FormId": form_id,
        "FieldKeys": field_keys,
        "FilterString": filter_string,
        "OrderString": order_string,
    }
    rows, exhausted, next_start, err = _paginate_bill(params, page_size, max_rows)
    if err is not None:
        return err
    result: dict = {"rows": rows, "row_count": len(rows), "exhausted": exhausted}
    if not exhausted:
        result["next_start_row"] = next_start
        result["hint"] = (
            "已达 max_rows 安全上限，如需继续请调用 query_bill_range 或缩小 filter_string 后手动分片"
        )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def query_bill_to_file(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    output_path: str = "",
    format: str = "ndjson",
    page_size: int = 2000,
    max_rows: int = 500000,
) -> str:
    """自动翻页并流式写入本地文件，适合大数据量导出（万行以上）。

    不在内存中累积数据，写入完成后返回文件路径和统计信息。
    文件可用 Read 工具抽检，或交由 pandas/polars 处理。

    返回格式：
        {"path": "...", "row_count": N, "bytes": M, "format": "ndjson"}
        若中途出错：{"error": "...", "path": "...", "row_count": <已写入>, "bytes": M}

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
        field_keys: 查询字段，逗号分隔。如 "FBillNo,FDate,FAmount"
        filter_string: 过滤条件。如 "FDate >= '2025-01-01'"
        output_path: 输出文件绝对路径。如 "/tmp/orders.ndjson"
        format: 输出格式，ndjson（每行一个 JSON 对象）或 csv，默认 ndjson
        page_size: 每页行数，默认 2000
        max_rows: 最大写入行数，默认 500000；超过则截断并正常返回
    """
    if not output_path or not os.path.isabs(output_path):
        return json.dumps({"error": "output_path 必须为非空绝对路径"}, ensure_ascii=False)
    if format not in {"ndjson", "csv"}:
        return json.dumps(
            {"error": f"format 必须是 ndjson 或 csv，收到: {format!r}"}, ensure_ascii=False
        )
    parent = os.path.dirname(output_path)
    if not os.path.isdir(parent):
        return json.dumps({"error": f"目录不存在: {parent}"}, ensure_ascii=False)

    fields = [f.strip() for f in field_keys.split(",") if f.strip()]
    params = {
        "FormId": form_id,
        "FieldKeys": field_keys,
        "FilterString": filter_string,
        "OrderString": "",
        "StartRow": 0,
    }

    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            rows_written, _, error_raw = _stream_to_file_handle(
                f, params, page_size, max_rows, fields, format, False
            )
    except OSError as e:
        return json.dumps({"error": f"文件写入失败: {e}"}, ensure_ascii=False)

    file_bytes = os.path.getsize(output_path)

    if error_raw is not None:
        return json.dumps(
            {
                "error": "查询中途遇到错误，已写入部分数据",
                "path": output_path,
                "row_count": rows_written,
                "bytes": file_bytes,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "path": output_path,
            "row_count": rows_written,
            "bytes": file_bytes,
            "format": format,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def query_bill_range(
    form_id: str,
    field_keys: str,
    date_field: str,
    date_from: str,
    date_to: str,
    extra_filter: str = "",
    chunk: str = "month",
    output_path: str = "",
    page_size: int = 2000,
) -> str:
    """按日期自动切片 + 翻页，适合跨月/跨年查询。

    将 [date_from, date_to) 按 chunk 切成 N 段，每段独立翻页拉取。
    output_path 为空时内联返回（受 MCP 1 MB 限制，适合小跨度）；
    非空时流式落盘，适合大跨度（年级）查询。

    返回格式（内联）：
        {"rows": [...], "row_count": N, "chunks": K, "exhausted": true}
    返回格式（落盘）：
        {"path": "...", "row_count": N, "bytes": M, "chunks": K, "format": "ndjson"}
        若中途出错：{"error": "...", "path": "...", "row_count": <已写入>, "bytes": M}

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder 等
        field_keys: 查询字段，逗号分隔
        date_field: 日期字段名。通常是 FDate 或 FCreateDate
        date_from: 起始日期（含），YYYY-MM-DD
        date_to: 结束日期（不含），YYYY-MM-DD
        extra_filter: 额外过滤条件（与日期条件 AND 拼接）
        chunk: 切片粒度，month（默认）/ week / day
        output_path: 落盘路径（绝对路径）。空=内联返回
        page_size: 每页行数，默认 2000
    """
    try:
        chunks = list(_iter_date_chunks(date_from, date_to, chunk))
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    inline_mode = not output_path

    if not inline_mode:
        if not os.path.isabs(output_path):
            return json.dumps({"error": "output_path 必须为绝对路径"}, ensure_ascii=False)
        parent = os.path.dirname(output_path)
        if not os.path.isdir(parent):
            return json.dumps({"error": f"目录不存在: {parent}"}, ensure_ascii=False)

    fields = [f.strip() for f in field_keys.split(",") if f.strip()]

    def _build_filter(chunk_from: str, chunk_to: str) -> str:
        date_filter = f"{date_field} >= '{chunk_from}' AND {date_field} < '{chunk_to}'"
        return f"({extra_filter}) AND {date_filter}" if extra_filter else date_filter

    if inline_mode:
        all_rows: list = []
        for chunk_from, chunk_to in chunks:
            params: dict = {
                "FormId": form_id,
                "FieldKeys": field_keys,
                "FilterString": _build_filter(chunk_from, chunk_to),
                "OrderString": "",
            }
            rows, _exhausted, _next, err = _paginate_bill(params, page_size, 20000)
            if err is not None:
                return err
            all_rows.extend(rows)
        return json.dumps(
            {
                "rows": all_rows,
                "row_count": len(all_rows),
                "chunks": len(chunks),
                "exhausted": True,
            },
            ensure_ascii=False,
        )

    # Streaming / file mode
    total_count = 0
    error_raw = None
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            header_written = False
            for chunk_from, chunk_to in chunks:
                params = {
                    "FormId": form_id,
                    "FieldKeys": field_keys,
                    "FilterString": _build_filter(chunk_from, chunk_to),
                    "OrderString": "",
                    "StartRow": 0,
                }
                rows_written, header_written, error_raw = _stream_to_file_handle(
                    f, params, page_size, 500000, fields, "ndjson", header_written
                )
                total_count += rows_written
                if error_raw is not None:
                    break
    except OSError as e:
        return json.dumps({"error": f"文件写入失败: {e}"}, ensure_ascii=False)

    file_bytes = os.path.getsize(output_path)

    if error_raw is not None:
        return json.dumps(
            {
                "error": "查询中途遇到错误，已写入部分数据",
                "path": output_path,
                "row_count": total_count,
                "bytes": file_bytes,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "path": output_path,
            "row_count": total_count,
            "bytes": file_bytes,
            "chunks": len(chunks),
            "format": "ndjson",
        },
        ensure_ascii=False,
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
    return _sdk().View(form_id, data)


@mcp.tool()
def query_metadata(form_id: str) -> str:
    """查询金蝶云星空表单的元数据（字段结构信息）。

    用于获取某个表单有哪些字段、字段类型等信息，便于构造查询和保存参数。

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
    """
    return _sdk().QueryBusinessInfo({"FormId": form_id})


@mcp.tool()
def save_bill(form_id: str, model_data: str) -> str:
    """保存金蝶云星空单据（新增或更新）。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        model_data: JSON格式的单据数据。示例（保存物料）：
            {"Model": {"FCreateOrgId": {"FNumber": "100"}, "FNumber": "MAT001", "FName": "物料名称"}}
            如果传入的JSON中没有"Model"键，会自动包装。
    """
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    try:
        data = json.loads(model_data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON in model_data: {e}"})
    if "Model" not in data:
        data = {"Model": data}
    return _sdk().Save(form_id, data)


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
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    return _sdk().Submit(form_id, _ids_data(numbers, ids))


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
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    return _sdk().Audit(form_id, _ids_data(numbers, ids))


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
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    return _sdk().UnAudit(form_id, _ids_data(numbers, ids))


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
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    return _sdk().Delete(form_id, _ids_data(numbers, ids))


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
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
    return _sdk().ExcuteOperation(form_id, op_number, _ids_data(numbers, ids))


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
        numbers: 源单编号，多个用逗号分隔
        ids: 源单内码ID，多个用逗号分隔（numbers 和 ids 二选一）
        rule_id: 转换规则ID（不填则用默认规则）
        target_form_id: 目标单据表单ID（不填则由规则决定）
        target_org_id: 目标组织ID，默认"0"
        target_bill_type_id: 目标单据类型ID（不填则用默认）
        is_enable_default_rule: 是否启用默认转换规则，默认"true"
        custom_params: 自定义参数JSON字符串。如 '{"FDATE":"2024-01-01"}'（不填则不传）
    """
    if _readonly:
        return json.dumps({"error": "只读模式：写入操作已禁用"})
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
    return _sdk().Push(form_id, data)


def setup() -> None:
    """Initialize environment, validate required vars, and create the SDK instance."""
    global api_sdk
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    _required_env = ["KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"]
    _missing_env = [k for k in _required_env if not os.getenv(k)]
    if _missing_env:
        raise RuntimeError(f"Missing required env vars: {', '.join(_missing_env)}")

    api_key = os.getenv("MCP_API_KEY", "")
    if api_key:
        issuer_url = os.getenv("MCP_ISSUER_URL", "http://localhost:8000")
        mcp._token_verifier = ApiKeyVerifier(api_key)
        mcp.settings.auth = AuthSettings(issuer_url=issuer_url, resource_server_url=issuer_url)  # type: ignore[arg-type]

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


def main():
    global _readonly
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Kingdee K3Cloud MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="传输协议（默认 stdio）",
    )
    parser.add_argument(
        "--mode",
        choices=["readonly", "readwrite"],
        default=os.environ.get("MCP_MODE", "readwrite"),
        help="readonly: 仅查询工具；readwrite: 全部工具（默认）",
    )
    args = parser.parse_args()

    _readonly = args.mode == "readonly"
    setup()

    _read_count = 8  # query_bill, query_bill_json, count_bill, query_bill_all, query_bill_to_file, query_bill_range, view_bill, query_metadata
    _write_count = 7  # save_bill, submit_bill, audit_bill, unaudit_bill, delete_bill, execute_operation, push_bill
    tool_count = _read_count if _readonly else _read_count + _write_count
    logger.info(f"[k3cloud] mode={args.mode}, tools={tool_count}")
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
