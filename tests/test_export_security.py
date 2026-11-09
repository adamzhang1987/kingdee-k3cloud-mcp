"""Issue #47: MCP callers can only create new files inside the export directory."""

import json
import logging
import os
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import MagicMock, patch

import pytest

import kingdee_k3cloud_mcp.server as server


@pytest.fixture(params=[False, True], ids=["readwrite", "readonly"])
def readonly(request, monkeypatch):
    monkeypatch.setattr(server, "_readonly", request.param)


@pytest.fixture(params=["query_bill_to_file", "query_bill_range"])
def export(request, monkeypatch, readonly):
    sdk = MagicMock()
    sdk.BillQuery.return_value = '[{"FID": 1}]'
    monkeypatch.setattr(server, "api_sdk", sdk)

    def call(filename, **kwargs):
        args = ("SAL_SaleOrder", "FID")
        if request.param == "query_bill_range":
            args += ("FDate", "2025-01-01", "2025-02-01")
        return json.loads(getattr(server, request.param)(*args, output_path=filename, **kwargs))

    return call, sdk


@pytest.mark.parametrize(
    "filename",
    [
        "/tmp/orders.ndjson",
        "../victim",
        "sub/orders.ndjson",
        "sub\\orders.ndjson",
        "C:\\orders.ndjson",
        "C:orders.ndjson",
        "\\\\host\\share\\orders.ndjson",
        "orders:stream",
        ".",
        "..",
        "orders\0.ndjson",
        "orders\n.ndjson",
        "orders.",
        "orders ",
        " ",
        "NUL",
        "nul.ndjson",
        "CON",
        "con .csv",
        "PRN.txt",
        "AUX",
        "COM1.txt",
        "lpt9",
        "COM¹.txt",
        "LPT².csv",
        "COM³",
        "CONIN$",
        "CONOUT$.txt",
        'bad".csv',
        "bad*.csv",
        "bad?.csv",
        "<bad>.csv",
        "a|b",
    ],
)
def test_unsafe_filename_rejected_before_query(export, tmp_path, filename):
    call, sdk = export
    result = call(filename)
    assert "error" in result
    sdk.BillQuery.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_outside_file_untouched(export, tmp_path):
    call, sdk = export
    outside = tmp_path.parent / f"{tmp_path.name}-victim.ndjson"
    outside.write_text("sentinel", encoding="utf-8")
    for name in (str(outside), f"../{outside.name}"):
        assert "error" in call(name)
        assert outside.read_text(encoding="utf-8") == "sentinel"
    sdk.BillQuery.assert_not_called()


def test_existing_file_never_overwritten(export, tmp_path):
    call, sdk = export
    target = tmp_path / "orders.ndjson"
    target.write_text("sentinel", encoding="utf-8")
    assert "error" in call(target.name)
    assert target.read_text(encoding="utf-8") == "sentinel"
    sdk.BillQuery.assert_not_called()


@pytest.mark.parametrize("link_kind", ["symlink", "dangling_symlink", "hardlink"])
def test_existing_links_never_followed(export, tmp_path, link_kind):
    call, sdk = export
    target = tmp_path.parent / f"{tmp_path.name}-target"
    if link_kind != "dangling_symlink":
        target.write_text("sentinel", encoding="utf-8")
    link = tmp_path / "orders.ndjson"
    try:
        if link_kind == "hardlink":
            os.link(target, link)
        else:
            link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"File links unavailable: {exc}")
    assert "error" in call(link.name)
    if link_kind == "dangling_symlink":
        assert not target.exists()
    else:
        assert target.read_text(encoding="utf-8") == "sentinel"
    sdk.BillQuery.assert_not_called()


def test_new_unicode_filename_returns_real_path_and_bytes(export, tmp_path):
    call, sdk = export
    # getsize must never be used: statistics come from the open file descriptor.
    with patch.object(server.os.path, "getsize", side_effect=AssertionError("path reopened")):
        result = call("销售订单.ndjson")
    target = tmp_path / "销售订单.ndjson"
    assert result["path"] == str(target.resolve())
    assert result["row_count"] == 1
    assert result["bytes"] == len(target.read_bytes())
    assert json.loads(target.read_text(encoding="utf-8")) == {"FID": 1}
    if os.name == "posix":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
    sdk.BillQuery.assert_called_once()


def test_concurrent_same_filename_only_one_succeeds(export, tmp_path):
    call, sdk = export
    barrier = Barrier(2)

    def attempt():
        barrier.wait(timeout=10)
        return call("orders.ndjson")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert sum("error" not in result for result in results) == 1
    assert json.loads((tmp_path / "orders.ndjson").read_text(encoding="utf-8")) == {"FID": 1}
    sdk.BillQuery.assert_called_once()


def test_uninitialized_directory_fails_closed(export, monkeypatch):
    call, sdk = export
    monkeypatch.setattr(server, "_export_dir", None)
    assert "error" in call("orders.ndjson")
    sdk.BillQuery.assert_not_called()


def test_creation_failure_does_not_query(export):
    call, sdk = export
    with patch.object(server, "_exclusive_export_opener", side_effect=PermissionError("denied")):
        assert "error" in call("orders.ndjson")
    sdk.BillQuery.assert_not_called()


def test_export_descriptor_is_not_inheritable():
    _, handle = server._open_export_file("private.ndjson")
    with handle:
        assert not os.get_inheritable(handle.fileno())
        handle.write("sentinel\n")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native handle ownership")
def test_windows_handle_closed_when_descriptor_conversion_fails(export, tmp_path, monkeypatch):
    import msvcrt

    call, sdk = export

    def fail_conversion(*args):
        raise OSError("descriptor conversion failed")

    monkeypatch.setattr(msvcrt, "open_osfhandle", fail_conversion)
    assert "error" in call("orders.ndjson")
    sdk.BillQuery.assert_not_called()
    # A leaked exclusive Windows handle would prevent this deletion.
    (tmp_path / "orders.ndjson").unlink()


@pytest.mark.parametrize("page_size", [0, -1])
def test_invalid_page_size_does_not_create_or_query(export, tmp_path, page_size):
    call, sdk = export
    assert "error" in call("orders.ndjson", page_size=page_size)
    assert list(tmp_path.iterdir()) == []
    sdk.BillQuery.assert_not_called()


@pytest.mark.parametrize("kwargs", [{"format": "xml"}, {"max_rows": 0}, {"max_rows": -1}])
def test_invalid_file_options_do_not_create_or_query(tmp_path, monkeypatch, kwargs):
    sdk = MagicMock()
    monkeypatch.setattr(server, "api_sdk", sdk)
    result = json.loads(
        server.query_bill_to_file("SAL_SaleOrder", "FID", output_path="out", **kwargs)
    )
    assert "error" in result
    assert list(tmp_path.iterdir()) == []
    sdk.BillQuery.assert_not_called()


def test_empty_filename_and_inline_contract(export, tmp_path, request):
    call, sdk = export
    result = call("")
    if request.node.callspec.params["export"] == "query_bill_range":
        assert result["rows"] == [{"FID": 1}]
        sdk.BillQuery.assert_called_once()
    else:
        assert "error" in result
        sdk.BillQuery.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_configured_directory_initialized_by_setup(monkeypatch, tmp_path, caplog, capsys):
    monkeypatch.setattr(server, "_export_dir", None)
    for key in ("KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"):
        monkeypatch.setenv(key, "test")
    monkeypatch.setenv("KD_STARTUP_CHECK", "0")
    with (
        patch.object(server, "load_dotenv"),
        patch.object(server, "DiagnosticK3CloudApiSdk"),
        caplog.at_level(logging.INFO),
    ):
        server.setup()
    assert server._export_dir == tmp_path.resolve()
    assert str(tmp_path.resolve()) in caplog.text
    assert capsys.readouterr().out == ""
    assert list(tmp_path.iterdir()) == []  # Write probe is removed.
    # Runtime changes to the environment cannot redirect an initialized instance.
    monkeypatch.setenv("KD_EXPORT_DIR", "/different")
    server._init_export_dir()
    assert server._export_dir == tmp_path.resolve()


@pytest.mark.parametrize("configured", [None, ""])
def test_default_directory_is_private_unique_and_not_auto_removed(
    monkeypatch, tmp_path, configured
):
    monkeypatch.setattr(server, "_export_dir", None)
    if configured is None:
        monkeypatch.delenv("KD_EXPORT_DIR")
    else:
        monkeypatch.setenv("KD_EXPORT_DIR", configured)
    # Keep generated test directories under pytest's cleanup directory.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    server._init_export_dir()
    first = server._export_dir
    assert first is not None
    assert first.parent == tmp_path.resolve()
    assert first.name.startswith("kingdee-export-")
    if os.name == "posix":
        assert stat.S_IMODE(first.stat().st_mode) == 0o700
    path, handle = server._open_export_file("orders.ndjson")
    with handle:
        handle.write("sentinel")
    monkeypatch.setattr(server, "_export_dir", None)
    server._init_export_dir()
    assert server._export_dir != first
    assert path.read_text(encoding="utf-8") == "sentinel"


def test_export_survives_process_exit(tmp_path):
    code = """
import os
from pathlib import Path
import tempfile
import kingdee_k3cloud_mcp.server as s
os.environ.pop('KD_EXPORT_DIR', None)
tempfile.tempdir = os.environ['EXPORT_TEST_TEMP']
s._init_export_dir()
path, handle = s._open_export_file('orders.ndjson')
with handle:
    handle.write('sentinel')
print(path)
"""
    env = {
        **os.environ,
        "EXPORT_TEST_TEMP": str(tmp_path),
        "PYTHONPATH": str(Path(server.__file__).parents[1]),
    }
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    path = Path(result.stdout.strip())
    assert path.parent.parent == tmp_path.resolve()
    assert path.read_text(encoding="utf-8") == "sentinel"


@pytest.mark.parametrize("kind", ["relative", "missing", "file", "unwritable"])
def test_invalid_config_fails_startup_without_fallback(monkeypatch, tmp_path, kind):
    monkeypatch.setattr(server, "_export_dir", None)
    configured = tmp_path
    if kind == "relative":
        monkeypatch.setenv("KD_EXPORT_DIR", "relative")
    else:
        if kind == "missing":
            configured = tmp_path / "missing"
        elif kind == "file":
            configured = tmp_path / "file"
            configured.write_text("sentinel", encoding="utf-8")
        monkeypatch.setenv("KD_EXPORT_DIR", str(configured))
    for key in ("KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"):
        monkeypatch.setenv(key, "test")
    with (
        patch.object(server, "load_dotenv"),
        patch.object(server, "DiagnosticK3CloudApiSdk") as sdk,
        patch.object(server.tempfile, "mkdtemp") as fallback,
        patch.object(server.tempfile, "TemporaryFile", side_effect=PermissionError("denied")),
        pytest.raises(RuntimeError, match="KD_EXPORT_DIR"),
    ):
        server.setup()
    assert server._export_dir is None
    fallback.assert_not_called()
    sdk.assert_not_called()


def test_configured_directory_canonicalized(monkeypatch, tmp_path):
    link = tmp_path / "alias"
    real = tmp_path / "real"
    real.mkdir()
    try:
        link.symlink_to(real, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Directory symlinks unavailable: {exc}")
    monkeypatch.setattr(server, "_export_dir", None)
    monkeypatch.setenv("KD_EXPORT_DIR", str(link))
    server._init_export_dir()
    path, handle = server._open_export_file("orders.ndjson")
    handle.close()
    assert path == real.resolve() / "orders.ndjson"
