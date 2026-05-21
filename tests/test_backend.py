"""Tests for explicit backend selection."""
import json
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import se


class Args:
    human = True
    caller = None
    no_interactive = False
    fzf = False
    query = ["needle"]
    scope = None
    path = None
    literal = True
    expand_only = False
    max = None
    max_seconds = None
    stats = False
    json = False
    log = False
    backend = None


def make_args(**overrides):
    args = Args()
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class TestResolveBackend:
    def test_windows_default_is_everything(self):
        with patch.object(se.platform, "system", return_value="Windows"):
            assert se.resolve_backend(None) == "everything"

    def test_non_windows_default_requires_explicit_backend(self):
        with patch.object(se.platform, "system", return_value="Linux"):
            with pytest.raises(se.BackendConfigError) as exc:
                se.resolve_backend(None)
        assert "require --backend" in str(exc.value)

    def test_everything_is_windows_only(self):
        with patch.object(se.platform, "system", return_value="Linux"):
            with pytest.raises(se.BackendConfigError) as exc:
                se.resolve_backend("everything")
        assert "Windows-only" in str(exc.value)

    def test_fd_and_rg_files_are_explicit_backends(self):
        with patch.object(se.platform, "system", return_value="Linux"):
            assert se.resolve_backend("fd") == "fd"
            assert se.resolve_backend("rg-files") == "rg-files"


class TestBackendSearch:
    def test_everything_uses_existing_single_path_function(self):
        with patch.object(se, "es_search", return_value=["one"]) as mock_search:
            assert se.backend_search("everything", "needle", "C:/root", None, 5, None) == ["one"]
        mock_search.assert_called_once_with("needle", "C:/root", 5, timeout=None)

    def test_everything_uses_existing_multi_path_function(self):
        with patch.object(se, "es_search_multi_path", return_value=["one"]) as mock_search:
            assert se.backend_search("everything", "needle", None, ["C:/a", "C:/b"], 5, 123.0) == ["one"]
        mock_search.assert_called_once_with("needle", ["C:/a", "C:/b"], 5, deadline=123.0)

    def test_fd_missing_fails_clearly(self):
        with patch.object(se.shutil, "which", return_value=None):
            with pytest.raises(se.BackendConfigError) as exc:
                se.backend_search("fd", "needle", None, None, 5, None)
        assert "requires fd in PATH" in str(exc.value)

    def test_rg_files_missing_fails_clearly(self):
        with patch.object(se.shutil, "which", return_value=None):
            with pytest.raises(se.BackendConfigError) as exc:
                se.backend_search("rg-files", "needle", None, None, 5, None)
        assert "requires rg in PATH" in str(exc.value)

    def test_fd_invokes_command_with_limit_and_path(self):
        with patch.object(se.shutil, "which", return_value="fd"), \
             patch.object(se, "_backend_invoke", return_value=("/tmp/one\n/tmp/two\n", 0, "")) as invoke:
            results = se.backend_search("fd", "needle", "/tmp", None, 1, None)
        assert results == ["/tmp/one"]
        argv, timeout = invoke.call_args[0]
        assert argv[:4] == ["fd", "--color", "never", "--absolute-path"]
        assert "--full-path" in argv
        assert "--max-results" in argv
        assert "1" in argv
        assert argv[-2:] == ["needle", "/tmp"]
        assert timeout is None

    def test_rg_files_filters_results_in_python(self):
        stdout = "src/se.py\nREADME.md\ntests/test_backend.py\n"
        with patch.object(se.shutil, "which", return_value="rg"), \
             patch.object(se, "_backend_invoke", return_value=(stdout, 0, "")):
            results = se.backend_search("rg-files", r"se\.py$", None, None, 5, None)
        assert len(results) == 1
        assert results[0].endswith(str(Path("src") / "se.py"))

    def test_backend_timeout_maps_to_search_timeout(self):
        deadline = time.monotonic() - 1
        with patch.object(se.shutil, "which", return_value="fd"):
            with pytest.raises(se.SearchTimeout):
                se.backend_search("fd", "needle", None, None, 5, deadline)


class TestCmdSearchObservation:
    def test_stats_include_backend(self, capsys):
        args = make_args(backend="fd", stats=True)
        with patch.object(se, "ensure_init"), \
             patch.object(se, "backend_search", return_value=["/tmp/needle"]), \
             patch.object(se.platform, "system", return_value="Linux"):
            se.cmd_search(args)
        err = capsys.readouterr().err
        assert "backend=fd" in err

    def test_json_includes_backend(self, capsys):
        args = make_args(backend="rg-files", json=True)
        with patch.object(se, "ensure_init"), \
             patch.object(se, "backend_search", return_value=["/tmp/needle"]), \
             patch.object(se.platform, "system", return_value="Linux"):
            se.cmd_search(args)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["backend"] == "rg-files"

    def test_log_includes_backend(self):
        args = make_args(backend="fd", log=True)
        with patch.object(se, "ensure_init"), \
             patch.object(se, "backend_search", return_value=["/tmp/needle"]), \
             patch.object(se, "append_log") as append_log, \
             patch.object(se, "detect_session_id", return_value=None), \
             patch.object(se.platform, "system", return_value="Linux"):
            se.cmd_search(args)
        entry = append_log.call_args[0][0]
        assert entry["backend"] == "fd"

    def test_non_interactive_still_rejects_fzf_before_search(self):
        args = make_args(backend="fd", fzf=True, no_interactive=True)
        with patch.object(se, "ensure_init"), pytest.raises(SystemExit) as exc:
            se.cmd_search(args)
        assert exc.value.code == 2


def test_invalid_backend_choice_exits_2():
    script = Path(__file__).resolve().parent.parent / "src" / "se.py"
    r = subprocess.run(
        [sys.executable, str(script), "--backend", "nope", "query"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 2
    assert "invalid choice" in r.stderr
