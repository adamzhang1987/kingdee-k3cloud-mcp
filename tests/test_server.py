import json
import os
import time
import unittest
from unittest.mock import MagicMock, patch

# Set required env vars before importing server module
os.environ.setdefault("KD_SERVER_URL", "http://test.example.com")
os.environ.setdefault("KD_ACCT_ID", "test_acct")
os.environ.setdefault("KD_USERNAME", "test_user")
os.environ.setdefault("KD_APP_ID", "test_app_id")
os.environ.setdefault("KD_APP_SEC", "test_app_sec")

from k3cloud_webapi_sdk.main import K3CloudApiSdk

from kingdee_k3cloud_mcp.server import SESSION_LOST_MSG, RetryableK3CloudApiSdk, _check_expired, _is_session_expired

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
        escaped = (
            '{"Result":{"ResponseStatus":{"Errors":[{"Message":"\\u4f1a\\u8bdd\\u4fe1\\u606f\\u5df2\\u4e22\\u5931\\uff0c\\u8bf7\\u91cd\\u65b0\\u767b\\u5f55"}]}}}'
        )
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
        with self._patch_parent_execute([EXPIRED_EXECUTEBILLQUERY, SUCCESS_EXECUTEBILLQUERY]) as mock_exec:
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


if __name__ == "__main__":
    unittest.main()
