import os
import sys
from pathlib import Path

from dotenv import load_dotenv


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
