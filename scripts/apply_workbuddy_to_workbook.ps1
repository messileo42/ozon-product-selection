param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'
$Node = 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$NodeModules = 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
if (-not (Test-Path -LiteralPath $Node)) {
    throw "找不到Codex内置Node.js：$Node"
}
if (-not (Test-Path -LiteralPath $NodeModules)) {
    throw "找不到Codex工作区依赖：$NodeModules"
}
$env:CODEX_WORKSPACE_NODE_MODULES = $NodeModules
& $Node (Join-Path $PSScriptRoot 'apply_workbuddy_to_workbook.mjs') @Arguments
exit $LASTEXITCODE
