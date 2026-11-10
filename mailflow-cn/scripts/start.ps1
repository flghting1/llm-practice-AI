param([ValidateSet('offline','openai')][string]$Mode = 'offline')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
python run.py --mode $Mode
