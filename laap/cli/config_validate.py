"""
LAAP — Configuration Validation

Schema-based config validation with helpful error messages.
Supports YAML and environment variable configuration sources.
"""

from __future__ import annotations
import json, logging, os, re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("laap.cli.config_validate")


@dataclass
class ValidationError:
    field: str
    message: str
    value: Any = None
    expected: str = ""

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "message": self.message,
            "value": str(self.value)[:100] if self.value is not None else None,
            "expected": self.expected,
        }


@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, field: str, message: str, value: Any = None,
                  expected: str = ""):
        self.errors.append(ValidationError(
            field=field, message=message, value=value, expected=expected,
        ))
        self.valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


class ConfigValidator:
    """Validates LAAP configuration values"""

    API_KEY_PATTERNS = {
        "openai": re.compile(r"^sk-(proj-)?[A-Za-z0-9]{20,}$"),
        "anthropic": re.compile(r"^sk-ant-[A-Za-z0-9]{32,}$"),
        "deepseek": re.compile(r"^[A-Za-z0-9]{20,}$"),
    }

    VALID_PROVIDERS = {"openai", "anthropic", "deepseek", "ollama", "openrouter"}

    def validate_all(self, config: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(valid=True)

        # Validate provider
        provider = config.get("provider", "")
        if provider and provider not in self.VALID_PROVIDERS:
            result.add_error(
                "provider", f"Unknown provider: {provider}",
                value=provider,
                expected=f"One of: {', '.join(self.VALID_PROVIDERS)}",
            )

        # Validate API key
        api_key = config.get("api_key", "")
        if api_key and provider in self.API_KEY_PATTERNS:
            pattern = self.API_KEY_PATTERNS[provider]
            if not pattern.match(api_key):
                result.add_warning(
                    f"API key for '{provider}' may be invalid "
                    f"(doesn't match expected format)"
                )

        # Validate model name
        model = config.get("model", "")
        if model and not re.match(r"^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)?$", model):
            result.add_error(
                "model", f"Invalid model name format: {model}",
                value=model, expected="e.g. gpt-4o, claude-sonnet-4-6",
            )

        # Validate temperature
        temp = config.get("temperature", None)
        if temp is not None:
            try:
                temp_f = float(temp)
                if temp_f < 0 or temp_f > 2:
                    result.add_error(
                        "temperature", "Must be between 0 and 2",
                        value=temp, expected="0.0 - 2.0",
                    )
            except (ValueError, TypeError):
                result.add_error(
                    "temperature", "Must be a number",
                    value=temp, expected="float",
                )

        # Validate timeout
        timeout = config.get("timeout", None)
        if timeout is not None:
            try:
                timeout_i = int(timeout)
                if timeout_i < 1 or timeout_i > 3600:
                    result.add_error(
                        "timeout", "Must be between 1 and 3600",
                        value=timeout, expected="1 - 3600",
                    )
            except (ValueError, TypeError):
                result.add_error(
                    "timeout", "Must be an integer",
                    value=timeout, expected="int",
                )

        # Validate max_tool_rounds
        max_rounds = config.get("max_tool_rounds", None)
        if max_rounds is not None:
            try:
                mr = int(max_rounds)
                if mr < 1 or mr > 100:
                    result.add_error(
                        "max_tool_rounds", "Must be between 1 and 100",
                        value=max_rounds,
                    )
            except (ValueError, TypeError):
                result.add_error(
                    "max_tool_rounds", "Must be an integer",
                    value=max_rounds,
                )

        return result

    def validate_api_key(self, provider: str, key: str) -> Tuple[bool, str]:
        """Validate a specific API key format."""
        if not key:
            return False, "API key is empty"
        if provider in self.API_KEY_PATTERNS:
            pattern = self.API_KEY_PATTERNS[provider]
            if pattern.match(key):
                return True, ""
            return False, f"API key doesn't match {provider} format"
        return True, ""  # Unknown provider, can't validate

    def suggest_fix(self, error: ValidationError) -> str:
        """Suggest a fix for a validation error."""
        fixes = {
            "provider": "Set LAAP_PROVIDER or check config file. Valid: openai, anthropic, deepseek, ollama",
            "api_key": "Set LAAP_API_KEY or use 'laap config' to configure",
            "model": "Check model name spelling, or use a known model like gpt-4o",
            "temperature": "Use a float between 0.0 and 2.0. Default is 0.7",
            "timeout": "Use an integer between 1 and 3600 seconds",
            "max_tool_rounds": "Use an integer between 1 and 100",
        }
        for key, suggestion in fixes.items():
            if key in error.field:
                return suggestion
        return "Check documentation for correct value format"


validator = ConfigValidator()
