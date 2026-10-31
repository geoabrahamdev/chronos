param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
& python (Join-Path $root "scripts\prepare_malecns_data.py") @Arguments
if ($LASTEXITCODE -ne 0) { throw "MaleCNS preparation failed with exit code $LASTEXITCODE" }
