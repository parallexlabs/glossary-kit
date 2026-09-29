from __future__ import annotations

import subprocess
import sys

import pytest

from glossary_kit.cli.main import app_main


def test_app_main_propagates_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    import glossary_kit.cli.main as main_module

    def _raise_exit() -> None:
        import typer

        raise typer.Exit(7)

    monkeypatch.setattr(main_module, "app", _raise_exit)
    with pytest.raises(SystemExit) as exc:
        app_main()
    assert exc.value.code == 7


def test_module_main_guard() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "glossary_kit.cli.main", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
