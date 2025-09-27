"""Project-specific Airflow package exposing custom plugins and utilities."""

from importlib import import_module
from typing import TYPE_CHECKING

plugins = import_module("airflow.plugins")

if TYPE_CHECKING:
    from . import plugins  # noqa: F401  # Re-export for static analyzers

__all__ = [
    "plugins",
]


