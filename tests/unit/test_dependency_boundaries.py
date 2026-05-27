from __future__ import annotations

import sys
from pathlib import Path

import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_dependencies_do_not_include_kraddr_base() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

    dependencies = pyproject["project"]["dependencies"]

    assert "python-kraddr-base" not in {dependency.split(">", 1)[0] for dependency in dependencies}


def test_package_import_does_not_load_kraddr_base() -> None:
    import datagokr  # noqa: F401

    assert "kraddr" not in sys.modules
    assert "kraddr_base" not in sys.modules


def test_source_does_not_expose_kraddr_base_types() -> None:
    source_text = "\n".join(
        path.read_text()
        for path in (PROJECT_ROOT / "src" / "datagokr").rglob("*.py")
    )

    assert "PlaceCoordinate" not in source_text
    assert "Address" not in source_text
