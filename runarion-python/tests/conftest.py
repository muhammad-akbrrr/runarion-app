import os
import sys
import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv

os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")


def pytest_addoption(parser):
    parser.addoption(
        "--mock-llm-provider",
        action="store_true",
        default=False,
        help="Run the novel pipeline E2E against the internal mock LLM provider.",
    )


TESTS_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = TESTS_DIR.parent
PROJECT_ROOT = PYTHON_ROOT.parent

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PYTHON_ROOT / ".env")

TEST_UPLOAD_PATH = Path("/tmp/runarion-pytest-upload")
TEST_UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("UPLOAD_PATH", str(TEST_UPLOAD_PATH))

TEST_OUTPUT_PATH = TESTS_DIR / "sample" / "output"
TEST_TEMP_OUTPUT_PATH = TEST_OUTPUT_PATH / "temp"
TEST_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
TEST_TEMP_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("PYTHONPATH", str(PYTHON_ROOT))
os.environ.setdefault("TEST_OUTPUT_PATH", str(TEST_OUTPUT_PATH))
os.environ.setdefault("TEST_EXPECTED_OUTPUTS_PATH", str(TEST_OUTPUT_PATH))
os.environ.setdefault("TEST_TEMP_OUTPUTS_PATH", str(TEST_TEMP_OUTPUT_PATH))
os.environ.setdefault("TEST_CONFIGS_PATH", str(TESTS_DIR / "sample"))
os.environ.setdefault("TEST_SAMPLE_FILES_PATH", str(TESTS_DIR / "sample"))


@pytest.fixture
def set_logger_level():
    adjusted_loggers: list[tuple[logging.Logger, int]] = []

    def _set(name: str, level: int) -> logging.Logger:
        logger = logging.getLogger(name)
        adjusted_loggers.append((logger, logger.level))
        logger.setLevel(level)
        return logger

    yield _set

    for logger, original_level in reversed(adjusted_loggers):
        logger.setLevel(original_level)
