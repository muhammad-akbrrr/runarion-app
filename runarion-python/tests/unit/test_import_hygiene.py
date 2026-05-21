import ast
from pathlib import Path


PYTHON_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PYTHON_ROOT / "src"
TEST_ROOT = PYTHON_ROOT / "tests"
BANNED_TOP_LEVEL = {"api", "models", "providers", "services", "utils", "config"}


def _iter_python_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def test_runtime_modules_use_package_imports():
    offenders = []

    for path in _iter_python_files(SRC_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and not node.module.startswith("."):
                    root = node.module.split(".", 1)[0]
                    if root in BANNED_TOP_LEVEL:
                        offenders.append(f"{path.relative_to(PYTHON_ROOT)}:{node.lineno} -> from {node.module} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root in BANNED_TOP_LEVEL:
                        offenders.append(f"{path.relative_to(PYTHON_ROOT)}:{node.lineno} -> import {alias.name}")

    assert not offenders, "Bare top-level runtime imports detected:\n- " + "\n- ".join(offenders[:50])


def test_tests_do_not_mutate_sys_path_per_file():
    offenders = []

    for path in _iter_python_files(TEST_ROOT):
        if path.name in {"conftest.py", "test_import_hygiene.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "sys.path.append(" in text or "sys.path.insert(" in text:
            offenders.append(str(path.relative_to(PYTHON_ROOT)))

    assert not offenders, "Per-test sys.path mutation detected:\n- " + "\n- ".join(offenders[:50])
