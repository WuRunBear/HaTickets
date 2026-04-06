$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))

function Get-PythonInvoker([string]$RootDir) {
    $venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        return @($venvPython)
    }

    $poetry = Get-Command poetry -ErrorAction SilentlyContinue
    if ($poetry) {
        return @($poetry.Path, "run", "python")
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Path)
    }

    return $null
}

$pythonInvoker = Get-PythonInvoker $repoRoot
if (-not $pythonInvoker) {
    Write-Host "❌ 未找到可用的 Python 环境"
    exit 1
}

Push-Location $repoRoot
try {
    if ($pythonInvoker.Count -eq 1) {
        & $pythonInvoker[0] "mobile/prompt_runner.py" @args
    } else {
        & $pythonInvoker[0] $pythonInvoker[1] $pythonInvoker[2] "mobile/prompt_runner.py" @args
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
