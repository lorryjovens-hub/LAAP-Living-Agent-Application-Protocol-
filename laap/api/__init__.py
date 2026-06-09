"""LAAP - API & CLI"""
# Lazy imports to avoid circular dependency chains
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from laap.api.server import app
    from laap.api.cli import main as cli

__all__ = ["app", "cli"]

def get_app():
    """Lazy load the FastAPI app."""
    from laap.api.server import app
    return app

def get_cli():
    """Lazy load the CLI main function."""
    from laap.api.cli import main
    return main
