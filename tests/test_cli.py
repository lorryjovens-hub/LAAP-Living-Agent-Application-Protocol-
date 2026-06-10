"""CLI tests — 5+ test functions covering help, subcommands, argument parsing."""

import pytest
from unittest.mock import MagicMock, patch
from typing import List


class TestMainHelp:
    """CLI help and argument parsing."""

    def test_main_help(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        help_text = parser.format_help()
        assert "usage:" in help_text.lower() or "usage" in help_text.lower()

    def test_parse_help_flag(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_parse_version_flag(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args(["--version"])
        assert args.version is True


class TestSubcommandImports:
    """Subcommand module imports."""

    def test_run_subcommand(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args(["run", "--agent", "test"])
        assert args.command == "run"
        assert args.agent == "test"

    def test_config_subcommand(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args(["config", "--show"])
        assert args.command == "config"

    def test_test_subcommand(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args(["test", "--module", "agent"])
        assert args.command == "test"

    def test_agent_subcommand(self):
        from laap.__main__ import create_parser
        parser = create_parser()
        args = parser.parse_args(["agent", "--list"])
        assert args.command == "agent"
