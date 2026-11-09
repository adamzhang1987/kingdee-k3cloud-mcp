import pytest

import kingdee_k3cloud_mcp.server as server


@pytest.fixture(autouse=True)
def isolate_export_directory(tmp_path, monkeypatch):
    """Never export into an operator's real directory or leave test exports behind."""
    directory = tmp_path.resolve()
    monkeypatch.setattr(server, "_export_dir", directory)
    monkeypatch.setenv("KD_EXPORT_DIR", str(directory))
