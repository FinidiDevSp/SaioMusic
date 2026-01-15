$ErrorActionPreference = "Stop"

if (-Not (Test-Path ".venv")) {
  py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
pre-commit install

Write-Host "Ready: venv + dev deps + pre-commit" -ForegroundColor Green
