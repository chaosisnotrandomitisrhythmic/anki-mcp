"""Tests for config module."""

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import anki_mcp.config as config_mod


@pytest.fixture(autouse=True)
def _reset_config_after_test():
    """Reload config with a clean env after each test to avoid cross-test state leak."""
    yield
    os.environ.pop("ANKI_MCP_ARCHIVE_DIR", None)
    importlib.reload(config_mod)


def _reload_config():
    importlib.reload(config_mod)
    return config_mod


def test_archive_dir_default():
    """Default ARCHIVE_DIR uses ~/.local/share/anki-mcp/archive."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANKI_MCP_ARCHIVE_DIR", None)
        cfg = _reload_config()
        assert cfg.ARCHIVE_DIR == Path.home() / ".local" / "share" / "anki-mcp" / "archive"


def test_archive_dir_env_override():
    """ANKI_MCP_ARCHIVE_DIR env var overrides default."""
    with patch.dict(os.environ, {"ANKI_MCP_ARCHIVE_DIR": "/tmp/test-archive"}):
        cfg = _reload_config()
        assert cfg.ARCHIVE_DIR == Path("/tmp/test-archive")


def test_archive_dir_tilde_expansion():
    """Env var with ~ is expanded."""
    with patch.dict(os.environ, {"ANKI_MCP_ARCHIVE_DIR": "~/my-archive"}):
        cfg = _reload_config()
        assert "~" not in str(cfg.ARCHIVE_DIR)
        assert cfg.ARCHIVE_DIR == Path.home() / "my-archive"


def test_constants():
    """Core constants are set."""
    from anki_mcp.config import ANKI_CONNECT_URL, ANKI_CONNECT_VERSION, DEFAULT_DECK, DEFAULT_MODEL
    assert ANKI_CONNECT_URL == "http://127.0.0.1:8765"
    assert ANKI_CONNECT_VERSION == 6
    assert DEFAULT_DECK == "Default"
    assert DEFAULT_MODEL == "Basic"
