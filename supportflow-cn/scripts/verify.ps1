$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:LANGSMITH_TRACING = 'false'
$env:SUPPORT_MODEL_PROVIDER = 'offline'
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests -q --junitxml=artifacts/pytest.xml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/evaluate.py --provider offline
exit $LASTEXITCODE
