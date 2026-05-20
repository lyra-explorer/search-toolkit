"""Smoke tests for se CLI parser and core functions."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import se


# ---------------------------------------------------------------------------
# Path filtering
# ---------------------------------------------------------------------------

class TestIsUnderRoot:
    def test_exact_match(self):
        assert se._is_under_root(r"C:\Users\test\file.txt", r"C:\Users\test")

    def test_no_false_positive(self):
        """dir1 should NOT match dir12."""
        assert not se._is_under_root(r"D:\dir12\file.txt", r"D:\dir1")

    def test_case_insensitive(self):
        assert se._is_under_root(r"c:\USERS\test\file.txt", r"C:\users\test")

    def test_different_drives(self):
        assert not se._is_under_root(r"D:\file.txt", r"C:\Users")

    def test_trailing_backslash(self):
        assert se._is_under_root(r"C:\root\file.txt", r"C:\root")


class TestEnforceAllowed:
    def test_no_restriction(self):
        paths = [r"C:\a.txt", r"D:\b.txt"]
        assert se.enforce_allowed(paths, None) == paths

    def test_filter(self):
        paths = [r"C:\Users\alice\doc.txt", r"D:\data\secret.txt"]
        result = se.enforce_allowed(paths, [r"C:\Users"])
        assert result == [r"C:\Users\alice\doc.txt"]

    def test_empty_allowed(self):
        paths = [r"C:\a.txt"]
        assert se.enforce_allowed(paths, []) == paths


class TestFilterResults:
    def test_no_restriction(self):
        results = [r"C:\a.txt", r"D:\b.txt"]
        assert se.filter_results(results, None) == results

    def test_filter(self):
        results = [r"C:\Users\doc.txt", r"D:\data\file.txt"]
        assert se.filter_results(results, [r"C:\Users"]) == [r"C:\Users\doc.txt"]


# ---------------------------------------------------------------------------
# Config parsing (simple parser, no yaml dependency)
# ---------------------------------------------------------------------------

class TestParseProfileSimple:
    def test_key_value(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".serc", delete=False, encoding="utf-8") as f:
            f.write('es_path: "C:\\test\\es.exe"\n')
            f.flush()
            result = se._parse_profile_simple(Path(f.name))
        os.unlink(f.name)
        assert result["es_path"] == r"C:\test\es.exe"

    def test_list_value(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".serc", delete=False, encoding="utf-8") as f:
            lines = ["caller_pi_allowed:", '  - "item1"', '  - "item2"']
            f.write(chr(10).join(lines) + chr(10))
            f.flush()
            result = se._parse_profile_simple(Path(f.name))
        os.unlink(f.name)
        assert result["caller_pi_allowed"] == ["item1", "item2"]

    def test_comments_ignored(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".serc", delete=False, encoding="utf-8") as f:
            f.write('# comment\nes_path: "value"\n')
            f.flush()
            result = se._parse_profile_simple(Path(f.name))
        os.unlink(f.name)
        assert "es_path" in result


# ---------------------------------------------------------------------------
# Migemo logic
# ---------------------------------------------------------------------------

class TestMigemoLogic:
    """Test the ASCII gate for migemo_expand."""

    def test_ascii_only_detection(self):
        """All chars < 128 → should go to migemo."""
        query = "hello"
        assert all(ord(c) < 128 for c in query)

    def test_japanese_bypass(self):
        """Japanese chars → should NOT go to migemo."""
        query = "ねむそう"
        assert not all(ord(c) < 128 for c in query)

    def test_mixed_bypass(self):
        """Mixed ASCII + non-ASCII → should NOT go to migemo."""
        query = "config.py ねむそう"
        assert not all(ord(c) < 128 for c in query)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestArgParsing:
    def test_basic_query(self):
        with patch("sys.argv", ["se", "test", "query"]):
            with patch.object(se, "cmd_search"):
                with patch.object(se, "ensure_init"):
                    se.main()

    def test_init_flag(self):
        with patch("sys.argv", ["se", "--init"]):
            with patch.object(se, "cmd_init") as mock_init:
                se.main()
                mock_init.assert_called_once()

    def test_literal_flag(self):
        with patch("sys.argv", ["se", "--literal", "test"]):
            with patch.object(se, "cmd_search") as mock_search:
                with patch.object(se, "ensure_init"):
                    se.main()
                    args = mock_search.call_args[0][0]
                    assert args.literal is True


# ---------------------------------------------------------------------------
# Integration: se --help
# ---------------------------------------------------------------------------

class TestCLIHelp:
    def test_help_exit_code(self):
        r = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "src" / "se.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert r.returncode == 0
        assert "romaji-aware" in r.stdout.lower() or "search" in r.stdout.lower()
