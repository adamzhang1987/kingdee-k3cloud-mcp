"""Contract tests for the 10 MCP tool functions that were not covered by test_server.py.

Covers: query_bill, query_bill_json, count_bill, view_bill, query_metadata,
        save_bill, submit_bill, audit_bill, unaudit_bill, delete_bill,
        execute_operation, push_bill
        plus: setup(), readonly guard, _sdk() helper.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

import kingdee_k3cloud_mcp.server as server_mod
from kingdee_k3cloud_mcp.server import (
    audit_bill,
    count_bill,
    delete_bill,
    execute_operation,
    push_bill,
    query_bill,
    query_bill_json,
    query_metadata,
    save_bill,
    setup,
    submit_bill,
    unaudit_bill,
    view_bill,
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
EXPIRED_JSON = json.dumps(_EXPIRED_DICT)
SUCCESS_ROWS = json.dumps([{"FNumber": "MAT001", "FName": "测试物料"}])
SUCCESS_2D = json.dumps([["MAT001", "测试物料"]])


def _mock_sdk(**method_map):
    """Return a MagicMock SDK with specific return values per method."""
    mock = MagicMock()
    for name, value in method_map.items():
        if isinstance(value, Exception):
            getattr(mock, name).side_effect = value
        else:
            getattr(mock, name).return_value = value
    return mock


@pytest.fixture(autouse=True)
def reset_readonly():
    """Ensure _readonly is False before each test."""
    server_mod._readonly = False
    yield
    server_mod._readonly = False


# ---------------------------------------------------------------------------
# _sdk() helper
# ---------------------------------------------------------------------------


class TestSdkHelper:
    def test_raises_when_api_sdk_is_none(self):
        with (
            patch.object(server_mod, "api_sdk", None),
            pytest.raises(AssertionError, match="not initialized"),
        ):
            server_mod._sdk()

    def test_returns_sdk_when_set(self):
        mock = MagicMock()
        with patch.object(server_mod, "api_sdk", mock):
            assert server_mod._sdk() is mock


# ---------------------------------------------------------------------------
# query_bill — ExecuteBillQuery → _wrap_query_result
# ---------------------------------------------------------------------------


class TestQueryBill:
    def test_happy_path_returns_wrapped_envelope(self):
        mock = _mock_sdk(ExecuteBillQuery=SUCCESS_2D)
        with patch.object(server_mod, "api_sdk", mock):
            result = json.loads(query_bill("SAL_SaleOrder", "FNumber,FName"))
        assert "rows" in result
        assert result["row_count"] == 1
        assert result["truncated"] is False

    def test_session_expired_passthrough(self):
        mock = _mock_sdk(ExecuteBillQuery=EXPIRED_JSON)
        with patch.object(server_mod, "api_sdk", mock):
            raw = query_bill("SAL_SaleOrder", "FID")
        assert raw == EXPIRED_JSON

    def test_sdk_exception_propagates(self):
        mock = _mock_sdk(ExecuteBillQuery=RuntimeError("network error"))
        with (
            patch.object(server_mod, "api_sdk", mock),
            pytest.raises(RuntimeError, match="network error"),
        ):
            query_bill("SAL_SaleOrder", "FID")

    def test_passes_params_to_sdk(self):
        mock = _mock_sdk(ExecuteBillQuery=SUCCESS_2D)
        with patch.object(server_mod, "api_sdk", mock):
            query_bill("BD_MATERIAL", "FName", filter_string="FNumber='X'", top_count=50)
        call_params = mock.ExecuteBillQuery.call_args[0][0]
        assert call_params["FormId"] == "BD_MATERIAL"
        assert call_params["FilterString"] == "FNumber='X'"
        assert call_params["TopRowCount"] == 50


# ---------------------------------------------------------------------------
# query_bill_json — BillQuery → _wrap_query_result
# ---------------------------------------------------------------------------


class TestQueryBillJson:
    def test_happy_path_returns_wrapped_envelope(self):
        mock = _mock_sdk(BillQuery=SUCCESS_ROWS)
        with patch.object(server_mod, "api_sdk", mock):
            result = json.loads(query_bill_json("SAL_SaleOrder", "FNumber,FName"))
        assert "rows" in result
        assert result["rows"][0]["FNumber"] == "MAT001"

    def test_session_expired_passthrough(self):
        mock = _mock_sdk(BillQuery=EXPIRED_JSON)
        with patch.object(server_mod, "api_sdk", mock):
            raw = query_bill_json("SAL_SaleOrder", "FID")
        assert raw == EXPIRED_JSON

    def test_truncated_when_hits_top_count(self):
        rows = json.dumps([{"FID": i} for i in range(10)])
        mock = _mock_sdk(BillQuery=rows)
        with patch.object(server_mod, "api_sdk", mock):
            result = json.loads(query_bill_json("SAL_SaleOrder", "FID", top_count=10))
        assert result["truncated"] is True
        assert "next_start_row" in result


# ---------------------------------------------------------------------------
# count_bill
# ---------------------------------------------------------------------------


class TestCountBill:
    def test_small_count_is_exact(self):
        rows = json.dumps([{"FID": i} for i in range(42)])
        mock = _mock_sdk(BillQuery=rows)
        with patch.object(server_mod, "api_sdk", mock):
            result = json.loads(count_bill("BD_MATERIAL", "FNumber='X'"))
        assert result["estimated_rows"] == 42
        assert result["is_exact"] is True
        assert "hint" not in result

    def test_large_count_not_exact_with_hint(self):
        rows = json.dumps([{"FID": i} for i in range(5000)])
        mock = _mock_sdk(BillQuery=rows)
        with patch.object(server_mod, "api_sdk", mock):
            result = json.loads(count_bill("SAL_SaleOrder"))
        assert result["estimated_rows"] == 5000
        assert result["is_exact"] is False
        assert "hint" in result

    def test_session_expired_passthrough(self):
        mock = _mock_sdk(BillQuery=EXPIRED_JSON)
        with patch.object(server_mod, "api_sdk", mock):
            raw = count_bill("SAL_SaleOrder")
        assert raw == EXPIRED_JSON

    def test_non_list_response_passthrough(self):
        non_list = json.dumps({"error": "something went wrong"})
        mock = _mock_sdk(BillQuery=non_list)
        with patch.object(server_mod, "api_sdk", mock):
            raw = count_bill("SAL_SaleOrder")
        assert raw == non_list

    def test_passes_filter_to_sdk(self):
        mock = _mock_sdk(BillQuery=json.dumps([]))
        with patch.object(server_mod, "api_sdk", mock):
            count_bill("SAL_SaleOrder", "FDate >= '2025-01-01'")
        call_params = mock.BillQuery.call_args[0][0]
        assert call_params["FilterString"] == "FDate >= '2025-01-01'"


# ---------------------------------------------------------------------------
# view_bill
# ---------------------------------------------------------------------------


class TestViewBill:
    def test_happy_path_returns_sdk_response(self):
        response = json.dumps({"FID": "12345", "FName": "Test"})
        mock = _mock_sdk(View=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = view_bill("BD_MATERIAL", number="MAT001")
        assert result == response
        mock.View.assert_called_once_with(
            "BD_MATERIAL", {"CreateOrgId": 0, "Number": "MAT001", "Id": "", "IsSortBySeq": "false"}
        )

    def test_view_by_id(self):
        mock = _mock_sdk(View="{}")
        with patch.object(server_mod, "api_sdk", mock):
            view_bill("BD_MATERIAL", bill_id="999")
        call_args = mock.View.call_args[0]
        assert call_args[1]["Id"] == "999"

    def test_sdk_exception_propagates(self):
        mock = _mock_sdk(View=RuntimeError("SDK error"))
        with patch.object(server_mod, "api_sdk", mock), pytest.raises(RuntimeError):
            view_bill("BD_MATERIAL", number="MAT001")


# ---------------------------------------------------------------------------
# query_metadata
# ---------------------------------------------------------------------------


class TestQueryMetadata:
    def test_happy_path_returns_sdk_response(self):
        response = json.dumps({"FormId": "SAL_SaleOrder", "Fields": []})
        mock = _mock_sdk(QueryBusinessInfo=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = query_metadata("SAL_SaleOrder")
        assert result == response
        mock.QueryBusinessInfo.assert_called_once_with({"FormId": "SAL_SaleOrder"})


# ---------------------------------------------------------------------------
# save_bill
# ---------------------------------------------------------------------------


class TestSaveBill:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(save_bill("BD_MATERIAL", '{"FName": "test"}'))
        assert "error" in result
        assert "只读" in result["error"]

    def test_invalid_json_returns_error(self):
        result = json.loads(save_bill("BD_MATERIAL", "not-json"))
        assert "error" in result
        assert "Invalid JSON" in result["error"]

    def test_auto_wraps_model_key(self):
        mock = _mock_sdk(Save='{"Result": {"IsSuccess": true}}')
        with patch.object(server_mod, "api_sdk", mock):
            save_bill("BD_MATERIAL", '{"FName": "物料名称"}')
        call_data = mock.Save.call_args[0][1]
        assert "Model" in call_data
        assert call_data["Model"]["FName"] == "物料名称"

    def test_model_key_not_double_wrapped(self):
        mock = _mock_sdk(Save='{"Result": {"IsSuccess": true}}')
        with patch.object(server_mod, "api_sdk", mock):
            save_bill("BD_MATERIAL", '{"Model": {"FName": "物料名称"}}')
        call_data = mock.Save.call_args[0][1]
        assert "Model" in call_data
        assert "Model" not in call_data["Model"]

    def test_happy_path_returns_sdk_response(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(Save=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = save_bill("BD_MATERIAL", '{"FName": "物料"}')
        assert result == response


# ---------------------------------------------------------------------------
# submit_bill
# ---------------------------------------------------------------------------


class TestSubmitBill:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(submit_bill("SAL_SaleOrder", numbers="SO001"))
        assert "error" in result

    def test_happy_path_by_numbers(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(Submit=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = submit_bill("SAL_SaleOrder", numbers="SO001,SO002")
        assert result == response
        call_data = mock.Submit.call_args[0][1]
        assert call_data["Numbers"] == ["SO001", "SO002"]

    def test_happy_path_by_ids(self):
        mock = _mock_sdk(Submit="{}")
        with patch.object(server_mod, "api_sdk", mock):
            submit_bill("SAL_SaleOrder", ids="123,456")
        call_data = mock.Submit.call_args[0][1]
        assert call_data["Ids"] == ["123", "456"]


# ---------------------------------------------------------------------------
# audit_bill
# ---------------------------------------------------------------------------


class TestAuditBill:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(audit_bill("SAL_SaleOrder", numbers="SO001"))
        assert "error" in result

    def test_happy_path(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(Audit=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = audit_bill("SAL_SaleOrder", numbers="SO001")
        assert result == response


# ---------------------------------------------------------------------------
# unaudit_bill
# ---------------------------------------------------------------------------


class TestUnauditBill:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(unaudit_bill("SAL_SaleOrder", numbers="SO001"))
        assert "error" in result

    def test_happy_path(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(UnAudit=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = unaudit_bill("SAL_SaleOrder", numbers="SO001")
        assert result == response


# ---------------------------------------------------------------------------
# delete_bill
# ---------------------------------------------------------------------------


class TestDeleteBill:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(delete_bill("SAL_SaleOrder", numbers="SO001"))
        assert "error" in result

    def test_happy_path(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(Delete=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = delete_bill("SAL_SaleOrder", numbers="SO001")
        assert result == response

    def test_comma_separated_numbers(self):
        mock = _mock_sdk(Delete="{}")
        with patch.object(server_mod, "api_sdk", mock):
            delete_bill("SAL_SaleOrder", numbers=" SO001 , SO002 ")
        call_data = mock.Delete.call_args[0][1]
        assert call_data["Numbers"] == ["SO001", "SO002"]


# ---------------------------------------------------------------------------
# execute_operation
# ---------------------------------------------------------------------------


class TestExecuteOperation:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(execute_operation("BD_MATERIAL", "Forbid", numbers="MAT001"))
        assert "error" in result

    def test_happy_path(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(ExcuteOperation=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = execute_operation("BD_MATERIAL", "Forbid", numbers="MAT001")
        assert result == response
        mock.ExcuteOperation.assert_called_once()
        assert mock.ExcuteOperation.call_args[0][1] == "Forbid"

    def test_enable_operation(self):
        mock = _mock_sdk(ExcuteOperation="{}")
        with patch.object(server_mod, "api_sdk", mock):
            execute_operation("BD_MATERIAL", "Enable", ids="123")
        assert mock.ExcuteOperation.call_args[0][1] == "Enable"


# ---------------------------------------------------------------------------
# push_bill
# ---------------------------------------------------------------------------


class TestPushBill:
    def test_readonly_guard(self):
        server_mod._readonly = True
        result = json.loads(push_bill("SAL_SaleOrder", numbers="SO001"))
        assert "error" in result

    def test_happy_path_no_custom_params(self):
        response = '{"Result": {"IsSuccess": true}}'
        mock = _mock_sdk(Push=response)
        with patch.object(server_mod, "api_sdk", mock):
            result = push_bill(
                "SAL_SaleOrder", numbers="SO001", target_form_id="SAL_DeliveryNotice"
            )
        assert result == response
        call_data = mock.Push.call_args[0][1]
        assert call_data["Numbers"] == ["SO001"]
        assert "CustomParams" not in call_data

    def test_valid_custom_params_parsed(self):
        mock = _mock_sdk(Push="{}")
        with patch.object(server_mod, "api_sdk", mock):
            push_bill("SAL_SaleOrder", numbers="SO001", custom_params='{"FDATE": "2025-01-01"}')
        call_data = mock.Push.call_args[0][1]
        assert call_data["CustomParams"] == {"FDATE": "2025-01-01"}

    def test_invalid_custom_params_returns_error(self):
        result = json.loads(push_bill("SAL_SaleOrder", numbers="SO001", custom_params="not-json"))
        assert "error" in result
        assert "Invalid JSON" in result["error"]


# ---------------------------------------------------------------------------
# setup()
# ---------------------------------------------------------------------------


class TestSetup:
    def test_missing_env_vars_raises_runtime_error(self, monkeypatch):
        for key in ["KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"]:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("KD_SERVER_URL", "http://example.com")
        # Only KD_SERVER_URL set → missing the other 4
        with pytest.raises(RuntimeError, match="Missing required env vars"):
            setup()

    def test_all_env_vars_set_creates_sdk(self, monkeypatch):
        monkeypatch.setenv("KD_SERVER_URL", "http://example.com")
        monkeypatch.setenv("KD_ACCT_ID", "acct")
        monkeypatch.setenv("KD_USERNAME", "user")
        monkeypatch.setenv("KD_APP_ID", "appid")
        monkeypatch.setenv("KD_APP_SEC", "secret")

        mock_sdk_instance = MagicMock()
        with patch(
            "kingdee_k3cloud_mcp.server.RetryableK3CloudApiSdk", return_value=mock_sdk_instance
        ):
            setup()

        assert server_mod.api_sdk is mock_sdk_instance
        mock_sdk_instance.InitConfig.assert_called_once()

    def test_readonly_mode_set_by_main(self, monkeypatch):
        monkeypatch.setenv("KD_SERVER_URL", "http://example.com")
        monkeypatch.setenv("KD_ACCT_ID", "acct")
        monkeypatch.setenv("KD_USERNAME", "user")
        monkeypatch.setenv("KD_APP_ID", "appid")
        monkeypatch.setenv("KD_APP_SEC", "secret")

        with (
            patch("kingdee_k3cloud_mcp.server.RetryableK3CloudApiSdk", return_value=MagicMock()),
            patch("sys.argv", ["server", "--mode", "readonly"]),
            patch("kingdee_k3cloud_mcp.server.mcp") as mock_mcp,
        ):
            mock_mcp.run = MagicMock()  # prevent actual server start
            server_mod.main()

        assert server_mod._readonly is True


if __name__ == "__main__":
    import unittest

    unittest.main()
