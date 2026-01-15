$ErrorActionPreference = "Stop"

. .\.venv\Scripts\Activate.ps1
ruff check src tests
black --check src tests
mypy src
pytest -q
