param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ArgsForOms
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "C:\Users\75859\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

$env:PYTHONPATH = $Root
& $Python -m oms_v1 @ArgsForOms
