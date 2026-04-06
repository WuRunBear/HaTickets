$ErrorActionPreference = "Stop"

function Resolve-FullPath([string]$Target) {
    if ([System.IO.Path]::IsPathRooted($Target)) {
        return [System.IO.Path]::GetFullPath($Target)
    }
    return [System.IO.Path]::GetFullPath((Join-Path -Path (Get-Location) -ChildPath $Target))
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-FullPath (Join-Path $scriptDir "..\..")
$defaultConfigFile = Join-Path $repoRoot "mobile\config.jsonc"
$configOverride = ""

$hasRuns = $false
for ($i = 0; $i -lt $args.Length; $i++) {
    $token = [string]$args[$i]
    if ($token -match '^--runs($|=)') {
        $hasRuns = $true
        continue
    }
    if ($token -eq "--config") {
        if ($i + 1 -ge $args.Length) {
            Write-Host "❌ --config 需要一个文件路径"
            exit 1
        }
        $configOverride = Resolve-FullPath ([string]$args[$i + 1])
        $i++
        continue
    }
    if ($token -match '^--config=(.+)$') {
        $configOverride = Resolve-FullPath $matches[1]
        continue
    }
}

if ($configOverride) {
    $configFile = $configOverride
} elseif ($env:HATICKETS_CONFIG_PATH -and $env:HATICKETS_CONFIG_PATH.Trim()) {
    $configFile = Resolve-FullPath $env:HATICKETS_CONFIG_PATH.Trim()
} else {
    $configFile = $defaultConfigFile
}

$adb = "adb"
$deviceOutput = & $adb devices 2>$null
$deviceLines = @($deviceOutput | Where-Object { $_ -match '^\S+\s+device$' })
if ($deviceLines.Count -lt 1) {
    Write-Host "❌ 未检测到已连接的 Android 设备"
    Write-Host "   请通过 USB 连接设备并开启 USB 调试模式"
    exit 1
}

if (-not (Test-Path -LiteralPath $configFile -PathType Leaf)) {
    Write-Host "❌ 配置文件不存在: $configFile"
    Write-Host "   可先复制模板: cp mobile/config.example.jsonc mobile/config.jsonc"
    exit 1
}

$finalArgs = @($args)
if (-not $hasRuns) {
    $finalArgs += @("--runs", "1")
}

Write-Host "⏱️  开始模拟抢票流程压测（不提交订单）..."
Write-Host "   请确保手机已停在目标演出详情页（detail_page）"
Write-Host "   当前配置文件: $configFile"
Write-Host "   本脚本会强制使用安全模式: if_commit_order=false, auto_navigate=false, rush_mode=true"
Write-Host "   会输出每一步日志和相邻步骤耗时（+Xs）"
Write-Host ""

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

$env:HATICKETS_CONFIG_PATH = $configFile
Push-Location $repoRoot
try {
    if ($pythonInvoker.Count -eq 1) {
        & $pythonInvoker[0] "mobile/hot_path_benchmark.py" @finalArgs
    } else {
        & $pythonInvoker[0] $pythonInvoker[1] $pythonInvoker[2] "mobile/hot_path_benchmark.py" @finalArgs
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
