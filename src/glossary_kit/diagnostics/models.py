from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    path: str
    message: str
    rule_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


def format_diagnostics_text(diagnostics: list[Diagnostic]) -> str:
    lines: list[str] = []
    for d in diagnostics:
        prefix = d.severity.value.upper()
        lines.append(f"[{prefix}] {d.code} at {d.path}: {d.message}")
    return "\n".join(lines)


def format_diagnostics_json(diagnostics: list[Diagnostic]) -> str:
    return json.dumps([d.to_dict() for d in diagnostics], indent=2)


def format_diagnostics_sarif(diagnostics: list[Diagnostic], tool_name: str = "glossary-kit") -> str:
    error_diags = [d for d in diagnostics if d.severity == Severity.ERROR]
    results: list[dict[str, Any]] = []
    for d in error_diags:
        results.append(
            {
                "ruleId": d.code,
                "level": "error",
                "message": {"text": d.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": d.path.split("[", 1)[0] or "glossary.yaml"},
                            "region": {"message": {"text": d.path}},
                        }
                    }
                ],
            }
        )
    sarif: dict[str, Any] = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "informationUri": "https://github.com/parallexlabs/glossary-kit",
                        "rules": [
                            {
                                "id": d.code,
                                "shortDescription": {"text": d.message[:120]},
                            }
                            for d in error_diags
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)
