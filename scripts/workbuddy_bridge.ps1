[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BridgeArguments
)

$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'workbuddy_bridge.py'
$pythonPath = $env:WORKBUDDY_BRIDGE_PYTHON

if (-not $pythonPath) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*\WindowsApps\python.exe') {
        $pythonPath = $command.Source
    }
}

if (-not $pythonPath) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) {
        $pythonPath = $bundledPython
    }
}

if (-not $pythonPath -or -not (Test-Path -LiteralPath $pythonPath)) {
    throw '找不到可用的Python。请通过WORKBUDDY_BRIDGE_PYTHON指定python.exe。'
}

& $pythonPath $scriptPath @BridgeArguments
exit $LASTEXITCODE
