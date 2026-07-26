"""Export packaging (Phase 8). Unit checks + the real AC-04/AC-06 proof: an exported project
builds and passes its own tests in a clean container. No infra needed for the unit tests."""

import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest

from app.export_service import assemble_files, build_archive


class _Code:
    def __init__(self, path: str, content: str) -> None:
        self.path = path
        self.content = content


class _Doc:
    def __init__(self, type: str, content: str) -> None:
        self.type = type
        self.content = content


# A tiny but genuinely runnable Python project standing in for generated artifacts.
MINI = {
    "pyproject.toml": (
        '[project]\nname = "genproj"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n\n'
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["app"]\n'
    ),
    "app/__init__.py": "",
    "app/calc.py": "def add(a, b):\n    return a + b\n",
    "tests/test_calc.py": (
        "from app.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    ),
}


def test_assemble_adds_default_infra_without_genesis_refs() -> None:
    code = [_Code(p, c) for p, c in MINI.items()]
    files = assemble_files("Gen Proj", code, [_Doc("readme", "# Gen\n")])

    assert "Dockerfile" in files
    assert ".github/workflows/ci.yml" in files
    assert files["README.md"] == "# Gen\n"  # a real README doc wins over the default
    # NFR-09: nothing in the archive imports or depends on GenesisAI.
    assert "genesis" not in "\n".join(files.values()).lower()


def test_build_archive_roundtrip() -> None:
    data = build_archive({"a.txt": "hello", "b/c.txt": "world"})
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert set(z.namelist()) == {"a.txt", "b/c.txt"}
        assert z.read("b/c.txt") == b"world"


def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@pytest.mark.skipif(not _docker_ready(), reason="docker daemon not available")
def test_exported_project_builds_and_passes_in_container() -> None:  # AC-04, AC-06
    files = assemble_files("genproj", [_Code(p, c) for p, c in MINI.items()], [])
    data = build_archive(files)
    tag = "genesis-export-test:latest"

    with tempfile.TemporaryDirectory() as d:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(d)
        root = Path(d)
        for required in (
            "Dockerfile",
            ".github/workflows/ci.yml",
            "README.md",
            "tests/test_calc.py",
        ):
            assert (root / required).exists(), required  # AC-06 contents

        try:
            build = subprocess.run(
                ["docker", "build", "-t", tag, d],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
            assert build.returncode == 0, build.stdout + build.stderr  # installs + builds
            run = subprocess.run(
                ["docker", "run", "--rm", tag],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
            )
            assert run.returncode == 0, run.stdout + run.stderr  # its generated tests pass
        finally:
            subprocess.run(["docker", "rmi", "-f", tag], capture_output=True)
