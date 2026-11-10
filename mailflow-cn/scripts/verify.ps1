$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:LANGSMITH_TRACING = 'false'
$env:MAIL_MODEL_PROVIDER = 'offline'
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest portfolio_tests -q --junitxml=artifacts/pytest.xml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/evaluate.py --provider offline
exit $LASTEXITCODE
