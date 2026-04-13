import json
import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from k3cloud_webapi_sdk.main import K3CloudApiSdk

import kingdee_k3cloud_mcp.server as _server_mod
from kingdee_k3cloud_mcp.server import (
    RetryableK3CloudApiSdk,
    _check_expired,
    _is_session_expired,
    _iter_date_chunks,
    _wrap_query_result,
    query_bill_all,
    query_bill_range,
    query_bill_to_file,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EXPIRED_DICT = {
    "Result": {
        "ResponseStatus": {
            "ErrorCode": 500,
            "IsSuccess": False,
            "Errors": [{"FieldName": None, "Message": "会话信息已丢失，请重新登录", "DIndex": 0}],
            "SuccessEntitys": [],
            "SuccessMessages": [],
            "MsgCode": 1,
        }
    }
}

# BillQuery: plain JSON object
EXPIRED_BILLQUERY = json.dumps(_EXPIRED_DICT)
SUCCESS_BILLQUERY = json.dumps([{"FNumber": "MAT001", "FName": "测试物料"}])

# ExecuteBillQuery: wrapped in [[...]]
EXPIRED_EXECUTEBILLQUERY = json.dumps([[_EXPIRED_DICT]])
SUCCESS_EXECUTEBILLQUERY = json.dumps([["MAT001", "测试物料"]])


# ---------------------------------------------------------------------------
# _check_expired
# ---------------------------------------------------------------------------


class TestCheckExpired(unittest.TestCase):
    def test_dict_session_expired(self):
        self.assertTrue(_check_expired(_EXPIRED_DICT))

    def test_list_wrapped_session_expired(self):
        """ExecuteBillQuery wraps response in [[...]]."""
        self.assertTrue(_check_expired([[_EXPIRED_DICT]]))

    def test_success_dict_returns_false(self):
        self.assertFalse(_check_expired({"FNumber": "MAT001", "FName": "测试物料"}))

    def test_empty_list_returns_false(self):
        self.assertFalse(_check_expired([]))

    def test_non_container_returns_false(self):
        self.assertFalse(_check_expired("some string"))
        self.assertFalse(_check_expired(None))
        self.assertFalse(_check_expired(42))


# ---------------------------------------------------------------------------
# _is_session_expired
# ---------------------------------------------------------------------------


class TestIsSessionExpired(unittest.TestCase):
    def test_billquery_expired(self):
        self.assertTrue(_is_session_expired(EXPIRED_BILLQUERY))

    def test_executebillquery_expired(self):
        """Must also detect session expiry in the [[...]] wrapped format."""
        self.assertTrue(_is_session_expired(EXPIRED_EXECUTEBILLQUERY))

    def test_billquery_success(self):
        self.assertFalse(_is_session_expired(SUCCESS_BILLQUERY))

    def test_executebillquery_success(self):
        self.assertFalse(_is_session_expired(SUCCESS_EXECUTEBILLQUERY))

    def test_invalid_json_returns_false(self):
        self.assertFalse(_is_session_expired("not json at all"))

    def test_empty_string_returns_false(self):
        self.assertFalse(_is_session_expired(""))

    def test_unicode_escaped_json(self):
        """Server may return unicode-escaped Chinese; json.loads decodes it back."""
        escaped = '{"Result":{"ResponseStatus":{"Errors":[{"Message":"\\u4f1a\\u8bdd\\u4fe1\\u606f\\u5df2\\u4e22\\u5931\\uff0c\\u8bf7\\u91cd\\u65b0\\u767b\\u5f55"}]}}}'
        self.assertTrue(_is_session_expired(escaped))


# ---------------------------------------------------------------------------
# RetryableK3CloudApiSdk.Execute
# ---------------------------------------------------------------------------


_INIT_KWARGS = dict(
    acct_id="test_acct",
    user_name="test_user",
    app_id="test_app_id",
    app_secret="test_app_sec",
    server_url="http://test.example.com",
)


class TestRetryableK3CloudApiSdk(unittest.TestCase):
    def setUp(self):
        self.sdk = RetryableK3CloudApiSdk("http://test.example.com")
        self.sdk.cookiesStore.SID = "old-session-id"
        self.sdk.cookiesStore.cookies = {"k": MagicMock()}

    def _patch_parent_execute(self, side_effect):
        """Patch K3CloudApiSdk.Execute (the super() target)."""
        return patch.object(K3CloudApiSdk, "Execute", side_effect=side_effect)

    # -- normal path ---------------------------------------------------------

    def test_success_returns_result(self):
        with self._patch_parent_execute([SUCCESS_BILLQUERY]) as mock_exec:
            result = self.sdk.Execute("some.service")

        self.assertEqual(result, SUCCESS_BILLQUERY)
        mock_exec.assert_called_once()

    def test_non_string_result_no_extra_call(self):
        """If parent returns a non-str, no session check or extra call."""
        with self._patch_parent_execute([{"unexpected": "dict"}]) as mock_exec:
            result = self.sdk.Execute("some.service")

        self.assertEqual(result, {"unexpected": "dict"})
        mock_exec.assert_called_once()

    # -- session expired, outside cooldown -----------------------------------

    def test_expired_returns_expired_result(self):
        """Execute always returns the original expired response — never a retry success."""
        with self._patch_parent_execute([EXPIRED_BILLQUERY, SUCCESS_BILLQUERY]):
            result = self.sdk.Execute("some.service")

        self.assertEqual(result, EXPIRED_BILLQUERY)

    @patch("time.monotonic", return_value=1000.0)
    def test_expired_outside_cooldown_makes_two_calls(self, _):
        """First call gets expired; second is fire-and-forget to re-establish SID."""
        with self._patch_parent_execute([EXPIRED_BILLQUERY, SUCCESS_BILLQUERY]) as mock_exec:
            self.sdk.Execute("some.service")

        self.assertEqual(mock_exec.call_count, 2)

    @patch("time.monotonic", return_value=1000.0)
    def test_expired_outside_cooldown_clears_cookiestore(self, _):
        """cookiesStore is replaced with a fresh instance (SID and cookies cleared)."""
        original_store = self.sdk.cookiesStore

        with self._patch_parent_execute([EXPIRED_BILLQUERY, SUCCESS_BILLQUERY]):
            self.sdk.Execute("some.service")

        self.assertIsNot(self.sdk.cookiesStore, original_store)
        self.assertEqual(self.sdk.cookiesStore.SID, "")
        self.assertEqual(self.sdk.cookiesStore.cookies, {})

    @patch("time.monotonic", return_value=1000.0)
    def test_expired_outside_cooldown_updates_reset_timestamp(self, _):
        """_session_reset_at is updated so the cooldown period starts."""
        self.assertEqual(self.sdk._session_reset_at, 0.0)

        before = time.monotonic()
        with self._patch_parent_execute([EXPIRED_BILLQUERY, SUCCESS_BILLQUERY]):
            self.sdk.Execute("some.service")
        after = time.monotonic()

        self.assertGreaterEqual(self.sdk._session_reset_at, before)
        self.assertLessEqual(self.sdk._session_reset_at, after)

    @patch("time.monotonic", return_value=1000.0)
    def test_executebillquery_expired_outside_cooldown(self, _):
        """[[...]] wrapped expiry also triggers the fire-and-forget reset."""
        with self._patch_parent_execute(
            [EXPIRED_EXECUTEBILLQUERY, SUCCESS_EXECUTEBILLQUERY]
        ) as mock_exec:
            result = self.sdk.Execute("some.service")

        self.assertEqual(result, EXPIRED_EXECUTEBILLQUERY)
        self.assertEqual(mock_exec.call_count, 2)

    # -- session expired, within cooldown ------------------------------------

    def test_expired_within_cooldown_makes_one_call(self):
        """Within cooldown: no fire-and-forget call — preserves the activating SID."""
        self.sdk._session_reset_at = time.monotonic()  # just reset

        with self._patch_parent_execute([EXPIRED_BILLQUERY]) as mock_exec:
            result = self.sdk.Execute("some.service")

        self.assertEqual(result, EXPIRED_BILLQUERY)
        mock_exec.assert_called_once()

    def test_expired_within_cooldown_preserves_cookiestore(self):
        """Within cooldown: cookiesStore is NOT replaced (new SID must stay intact)."""
        self.sdk._session_reset_at = time.monotonic()
        original_store = self.sdk.cookiesStore

        with self._patch_parent_execute([EXPIRED_BILLQUERY]):
            self.sdk.Execute("some.service")

        self.assertIs(self.sdk.cookiesStore, original_store)

    def test_expired_within_cooldown_does_not_update_reset_timestamp(self):
        """Within cooldown: _session_reset_at is not updated."""
        recent = time.monotonic()
        self.sdk._session_reset_at = recent

        with self._patch_parent_execute([EXPIRED_BILLQUERY]):
            self.sdk.Execute("some.service")

        self.assertEqual(self.sdk._session_reset_at, recent)


# ---------------------------------------------------------------------------
# _wrap_query_result
# ---------------------------------------------------------------------------


def _make_rows(n: int) -> list:
    return [{"FID": i} for i in range(n)]


class TestWrapQueryResult(unittest.TestCase):
    # -- successful wrapping -------------------------------------------------

    def test_returns_envelope_structure(self):
        raw = json.dumps(_make_rows(10))
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertIn("rows", result)
        self.assertIn("row_count", result)
        self.assertIn("truncated", result)

    def test_row_count_matches(self):
        raw = json.dumps(_make_rows(42))
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertEqual(result["row_count"], 42)

    def test_rows_preserves_original_data(self):
        original = _make_rows(5)
        raw = json.dumps(original)
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertEqual(result["rows"], original)

    # -- truncated=false cases -----------------------------------------------

    def test_not_truncated_when_rows_less_than_cap(self):
        raw = json.dumps(_make_rows(50))
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertFalse(result["truncated"])
        self.assertNotIn("next_start_row", result)
        self.assertNotIn("hint", result)

    def test_not_truncated_when_empty(self):
        raw = json.dumps([])
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertFalse(result["truncated"])

    # -- truncated=true cases ------------------------------------------------

    def test_truncated_when_rows_equal_top_count(self):
        raw = json.dumps(_make_rows(50))
        result = json.loads(_wrap_query_result(raw, top_count=50, limit=2000, start_row=0))
        self.assertTrue(result["truncated"])

    def test_truncated_when_rows_equal_limit(self):
        raw = json.dumps(_make_rows(2000))
        result = json.loads(_wrap_query_result(raw, top_count=2000, limit=2000, start_row=0))
        self.assertTrue(result["truncated"])

    def test_cap_is_min_of_top_count_and_limit(self):
        # top_count=500 < limit=2000 → cap=500
        raw = json.dumps(_make_rows(500))
        result = json.loads(_wrap_query_result(raw, top_count=500, limit=2000, start_row=0))
        self.assertTrue(result["truncated"])

    def test_next_start_row_is_start_plus_count(self):
        raw = json.dumps(_make_rows(100))
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=200))
        self.assertTrue(result["truncated"])
        self.assertEqual(result["next_start_row"], 300)

    def test_hint_present_when_truncated(self):
        raw = json.dumps(_make_rows(100))
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertIn("hint", result)

    # -- passthrough for non-list / error responses --------------------------

    def test_session_expired_passthrough(self):
        """会话过期响应原样透传，不包装。"""
        self.assertEqual(
            _wrap_query_result(EXPIRED_BILLQUERY, top_count=100, limit=2000, start_row=0),
            EXPIRED_BILLQUERY,
        )

    def test_executebillquery_expired_passthrough(self):
        """[[...]] 格式会话过期也原样透传。"""
        self.assertEqual(
            _wrap_query_result(EXPIRED_EXECUTEBILLQUERY, top_count=100, limit=2000, start_row=0),
            EXPIRED_EXECUTEBILLQUERY,
        )

    def test_invalid_json_passthrough(self):
        bad = "not valid json"
        self.assertEqual(_wrap_query_result(bad, top_count=100, limit=2000, start_row=0), bad)

    def test_non_list_json_passthrough(self):
        """非列表 JSON 原样透传（如 API 错误 dict）。"""
        non_list = json.dumps({"error": "something"})
        self.assertEqual(
            _wrap_query_result(non_list, top_count=100, limit=2000, start_row=0),
            non_list,
        )

    # -- ExecuteBillQuery 2D array format ------------------------------------

    def test_executebillquery_format_wrapped(self):
        """ExecuteBillQuery 返回二维数组，也应正确计算行数。"""
        rows_2d = [["MAT001", "物料1"], ["MAT002", "物料2"]]
        raw = json.dumps(rows_2d)
        result = json.loads(_wrap_query_result(raw, top_count=100, limit=2000, start_row=0))
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["rows"], rows_2d)
        self.assertFalse(result["truncated"])


# ---------------------------------------------------------------------------
# Helpers shared by Phase 2 tests
# ---------------------------------------------------------------------------


def _make_page(n: int, offset: int = 0) -> str:
    """Return a JSON-serialised list of n dicts starting at offset."""
    return json.dumps([{"FID": i, "FName": f"row{i}"} for i in range(offset, offset + n)])


def _patch_sdk(side_effect):
    """Patch the module-level api_sdk so BillQuery returns given side_effect values."""
    mock = MagicMock()
    mock.BillQuery.side_effect = side_effect
    return patch.object(_server_mod, "api_sdk", mock)


# ---------------------------------------------------------------------------
# query_bill_all
# ---------------------------------------------------------------------------


class TestQueryBillAll(unittest.TestCase):
    def test_three_pages_exhausted(self):
        """3 pages of 2000/2000/500 rows → row_count=4500, exhausted=True."""
        pages = [_make_page(2000, 0), _make_page(2000, 2000), _make_page(500, 4000)]
        with _patch_sdk(pages):
            result = json.loads(query_bill_all("SAL_SaleOrder", "FID,FName", page_size=2000))
        self.assertEqual(result["row_count"], 4500)
        self.assertTrue(result["exhausted"])
        self.assertNotIn("next_start_row", result)

    def test_max_rows_truncation(self):
        """Two 2000-row pages, max_rows=3000 → truncated to 3000, exhausted=False."""
        pages = [_make_page(2000, 0), _make_page(2000, 2000)]
        with _patch_sdk(pages):
            result = json.loads(
                query_bill_all("SAL_SaleOrder", "FID", max_rows=3000, page_size=2000)
            )
        self.assertEqual(result["row_count"], 3000)
        self.assertFalse(result["exhausted"])
        self.assertEqual(result["next_start_row"], 3000)
        self.assertIn("hint", result)

    def test_session_expired_first_page(self):
        """Session expired on first page → raw expired JSON returned directly."""
        with _patch_sdk([EXPIRED_BILLQUERY]):
            result_raw = query_bill_all("SAL_SaleOrder", "FID")
        self.assertEqual(result_raw, EXPIRED_BILLQUERY)

    def test_mid_page_non_list_returns_partial(self):
        """Non-list response mid-pagination → error raw returned, first page data discarded."""
        non_list = json.dumps({"error": "unexpected"})
        with _patch_sdk([_make_page(10), non_list]):
            result_raw = query_bill_all("SAL_SaleOrder", "FID", page_size=10)
        # _paginate_bill returns error_raw on non-list; tool returns it directly
        self.assertEqual(result_raw, non_list)

    def test_single_page_less_than_page_size(self):
        """Single page with fewer rows than page_size → exhausted=True, no next_start_row."""
        with _patch_sdk([_make_page(42)]):
            result = json.loads(query_bill_all("SAL_SaleOrder", "FID", page_size=2000))
        self.assertEqual(result["row_count"], 42)
        self.assertTrue(result["exhausted"])


# ---------------------------------------------------------------------------
# query_bill_to_file
# ---------------------------------------------------------------------------


class TestQueryBillToFile(unittest.TestCase):
    def test_relative_path_rejected(self):
        result = json.loads(
            query_bill_to_file("SAL_SaleOrder", "FID", output_path="relative/path.ndjson")
        )
        self.assertIn("error", result)
        self.assertNotIn("path", result)

    def test_empty_path_rejected(self):
        result = json.loads(query_bill_to_file("SAL_SaleOrder", "FID", output_path=""))
        self.assertIn("error", result)

    def test_invalid_format_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.txt")
            result = json.loads(
                query_bill_to_file("SAL_SaleOrder", "FID", output_path=out, format="xml")
            )
        self.assertIn("error", result)

    def test_nonexistent_parent_dir_rejected(self):
        result = json.loads(
            query_bill_to_file(
                "SAL_SaleOrder", "FID", output_path="/nonexistent_dir_xyz/out.ndjson"
            )
        )
        self.assertIn("error", result)

    def test_ndjson_write_three_pages(self):
        """3 pages of 100 rows each → 300 ndjson lines, valid JSON on each line."""
        pages = [_make_page(100, 0), _make_page(100, 100), _make_page(100, 200), _make_page(0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.ndjson")
            with _patch_sdk(pages):
                result = json.loads(
                    query_bill_to_file("SAL_SaleOrder", "FID,FName", output_path=out, page_size=100)
                )
            self.assertEqual(result["row_count"], 300)
            self.assertEqual(result["format"], "ndjson")
            self.assertGreater(result["bytes"], 0)
            with open(out, encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(len(lines), 300)
            json.loads(lines[0])  # first line is valid JSON
            json.loads(lines[-1])  # last line is valid JSON

    def test_csv_write_header_and_rows(self):
        """CSV output: first line is header from field_keys, total lines = header + rows."""
        import csv as _csv

        pages = [_make_page(50, 0), _make_page(50, 50), _make_page(0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            with _patch_sdk(pages):
                result = json.loads(
                    query_bill_to_file(
                        "SAL_SaleOrder", "FID,FName", output_path=out, format="csv", page_size=50
                    )
                )
            self.assertEqual(result["row_count"], 100)
            with open(out, encoding="utf-8", newline="") as f:
                reader = _csv.reader(f)
                rows = list(reader)
            self.assertEqual(rows[0], ["FID", "FName"])  # header
            self.assertEqual(len(rows), 101)  # header + 100 data rows

    def test_session_expired_mid_write_returns_partial(self):
        """Session expiry after first page → error with partial row_count, file kept."""
        pages = [_make_page(10), EXPIRED_BILLQUERY]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.ndjson")
            with _patch_sdk(pages):
                result = json.loads(
                    query_bill_to_file("SAL_SaleOrder", "FID", output_path=out, page_size=10)
                )
            self.assertIn("error", result)
            self.assertEqual(result["row_count"], 10)
            self.assertTrue(os.path.exists(out))

    def test_max_rows_respected(self):
        """max_rows=50 with two 100-row pages → exactly 50 rows written."""
        pages = [_make_page(100, 0), _make_page(100, 100)]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.ndjson")
            with _patch_sdk(pages):
                result = json.loads(
                    query_bill_to_file(
                        "SAL_SaleOrder", "FID", output_path=out, page_size=100, max_rows=50
                    )
                )
            self.assertEqual(result["row_count"], 50)


# ---------------------------------------------------------------------------
# _iter_date_chunks / query_bill_range
# ---------------------------------------------------------------------------


class TestIterDateChunks(unittest.TestCase):
    def test_month_chunks_three_months(self):
        chunks = list(_iter_date_chunks("2025-01-01", "2025-04-01", "month"))
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], ("2025-01-01", "2025-02-01"))
        self.assertEqual(chunks[1], ("2025-02-01", "2025-03-01"))
        self.assertEqual(chunks[2], ("2025-03-01", "2025-04-01"))

    def test_month_chunks_year_boundary(self):
        chunks = list(_iter_date_chunks("2024-11-01", "2025-02-01", "month"))
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], ("2024-11-01", "2024-12-01"))
        self.assertEqual(chunks[1], ("2024-12-01", "2025-01-01"))
        self.assertEqual(chunks[2], ("2025-01-01", "2025-02-01"))

    def test_week_chunks(self):
        chunks = list(_iter_date_chunks("2025-01-01", "2025-01-22", "week"))
        self.assertEqual(len(chunks), 3)

    def test_day_chunks(self):
        chunks = list(_iter_date_chunks("2025-01-01", "2025-01-04", "day"))
        self.assertEqual(len(chunks), 3)

    def test_invalid_chunk_raises(self):
        with self.assertRaises(ValueError):
            list(_iter_date_chunks("2025-01-01", "2025-02-01", "quarter"))

    def test_date_to_before_date_from_raises(self):
        with self.assertRaises(ValueError):
            list(_iter_date_chunks("2025-03-01", "2025-01-01", "month"))

    def test_date_to_equal_date_from_raises(self):
        with self.assertRaises(ValueError):
            list(_iter_date_chunks("2025-01-01", "2025-01-01", "month"))

    def test_invalid_date_format_raises(self):
        with self.assertRaises(ValueError):
            list(_iter_date_chunks("2025/01/01", "2025/04/01", "month"))


class TestQueryBillRange(unittest.TestCase):
    def test_invalid_chunk_returns_error(self):
        result = json.loads(
            query_bill_range(
                "SAL_SaleOrder", "FID", "FDate", "2025-01-01", "2025-04-01", chunk="quarter"
            )
        )
        self.assertIn("error", result)

    def test_date_to_before_date_from_returns_error(self):
        result = json.loads(
            query_bill_range("SAL_SaleOrder", "FID", "FDate", "2025-04-01", "2025-01-01")
        )
        self.assertIn("error", result)

    def test_inline_mode_three_chunks(self):
        """3 monthly chunks × 10 rows = 30 total rows, chunks=3."""
        # 3 chunks, each returns 10 rows (< page_size → exhausted per chunk)
        pages = [_make_page(10)] * 3
        with _patch_sdk(pages):
            result = json.loads(
                query_bill_range(
                    "SAL_SaleOrder",
                    "FID,FName",
                    "FDate",
                    "2025-01-01",
                    "2025-04-01",
                    page_size=2000,
                )
            )
        self.assertEqual(result["row_count"], 30)
        self.assertEqual(result["chunks"], 3)
        self.assertTrue(result["exhausted"])
        self.assertIn("rows", result)

    def test_inline_extra_filter_included(self):
        """extra_filter is AND-combined with date filter in BillQuery call."""
        mock = MagicMock()
        mock.BillQuery.return_value = _make_page(5)
        with patch.object(_server_mod, "api_sdk", mock):
            query_bill_range(
                "SAL_SaleOrder",
                "FID",
                "FDate",
                "2025-01-01",
                "2025-02-01",
                extra_filter="FCustId='X'",
                chunk="month",
            )
        call_params = mock.BillQuery.call_args[0][0]
        fs = call_params["FilterString"]
        self.assertIn("FCustId='X'", fs)
        self.assertIn("FDate >= '2025-01-01'", fs)
        self.assertIn("AND", fs)

    def test_file_mode_three_chunks_ndjson(self):
        """3 monthly chunks each with 10 rows → 30 lines in ndjson file, chunks=3."""
        pages = [_make_page(10)] * 3
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "range.ndjson")
            with _patch_sdk(pages):
                result = json.loads(
                    query_bill_range(
                        "SAL_SaleOrder",
                        "FID,FName",
                        "FDate",
                        "2025-01-01",
                        "2025-04-01",
                        output_path=out,
                        page_size=2000,
                    )
                )
            self.assertEqual(result["row_count"], 30)
            self.assertEqual(result["chunks"], 3)
            self.assertEqual(result["format"], "ndjson")
            with open(out, encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertEqual(len(lines), 30)

    def test_file_mode_relative_path_rejected(self):
        result = json.loads(
            query_bill_range(
                "SAL_SaleOrder",
                "FID",
                "FDate",
                "2025-01-01",
                "2025-04-01",
                output_path="rel/path.ndjson",
            )
        )
        self.assertIn("error", result)

    def test_file_mode_session_expired_mid_chunk_returns_partial(self):
        """Session expires on second chunk → error returned, partial file kept."""
        pages = [_make_page(10), EXPIRED_BILLQUERY]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "range.ndjson")
            with _patch_sdk(pages):
                result = json.loads(
                    query_bill_range(
                        "SAL_SaleOrder",
                        "FID",
                        "FDate",
                        "2025-01-01",
                        "2025-03-01",  # 2 chunks
                        output_path=out,
                        page_size=2000,
                    )
                )
            self.assertIn("error", result)
            self.assertEqual(result["row_count"], 10)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
