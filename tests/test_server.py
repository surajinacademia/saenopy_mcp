"""Fast checks of input validation; they need no image data and no saenopy run."""
import pytest

from saenopy_mcp import server


def test_tools_are_listed_in_workflow_order():
    names = [tool.name for tool in server.mcp._tool_manager.list_tools()]
    assert names == ["estimate_displacement", "reconstruct_forces", "export_field", "inspect_result"]


def test_relative_paths_are_rejected():
    with pytest.raises(ValueError, match="absolute"):
        server.local_path("results/out.saenopy")


def test_new_file_refuses_to_overwrite(tmp_path):
    existing = tmp_path / "result.saenopy"
    existing.write_bytes(b"")
    with pytest.raises(FileExistsError):
        with server.new_file(str(existing), ".saenopy"):
            pass


def test_new_file_checks_suffix_and_parent(tmp_path):
    with pytest.raises(ValueError, match=".csv"):
        with server.new_file(str(tmp_path / "out.txt"), ".csv"):
            pass
    with pytest.raises(ValueError):
        with server.new_file(str(tmp_path / "missing" / "out.csv"), ".csv"):
            pass


def test_new_file_publishes_only_on_success(tmp_path):
    target = tmp_path / "out.csv"
    with server.new_file(str(target), ".csv") as stage:
        stage.write_text("x\n")
    assert target.read_text() == "x\n"
    assert not list(tmp_path.glob(".*.csv"))
    failed = tmp_path / "failed.csv"
    with pytest.raises(RuntimeError):
        with server.new_file(str(failed), ".csv") as stage:
            stage.write_text("partial")
            raise RuntimeError("stop")
    assert not failed.exists()


def test_stats_ignores_nonfinite_vectors():
    import numpy as np
    summary = server.stats(np.array([[3.0, 4.0, 0.0], [np.nan, 0.0, 0.0]]))
    assert summary == dict(nodes=2, finite_vectors=1, median_magnitude=5.0, max_magnitude=5.0)
