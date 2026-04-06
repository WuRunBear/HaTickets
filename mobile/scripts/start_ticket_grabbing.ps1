$ErrorActionPreference = "Stop"

function Resolve-FullPath([string]$Target) {
    if ([System.IO.Path]::IsPathRooted($Target)) {
        return [System.IO.Path]::GetFullPath($Target)
    }
    return [System.IO.Path]::GetFullPath((Join-Path -Path (Get-Location) -ChildPath $Target))
}

function Find-AndroidHome() {
    if ($env:ANDROID_HOME -and $env:ANDROID_HOME.Trim()) {
        return $env:ANDROID_HOME.Trim()
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Android\Sdk"),
        (Join-Path $env:USERPROFILE "AppData\Local\Android\Sdk"),
        "C:\Android\Sdk"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Container)) {
            return $candidate
        }
    }

    return $null
}

function Get-AdbCommand([string]$AndroidHome) {
    if ($AndroidHome) {
        $adb = Join-Path $AndroidHome "platform-tools\adb.exe"
        if (Test-Path -LiteralPath $adb -PathType Leaf) {
            return $adb
        }
    }
    return "adb"
}

function Get-PythonCommand([string]$RootDir) {
    $venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        return $venvPython
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Path
    }

    return $null
}

function Get-ConfigFlag([string]$ConfigText, [string]$Key) {
    $escapedKey = [regex]::Escape($Key)
    if ($ConfigText -match "`"$escapedKey`"\s*:\s*true") {
        return "true"
    }
    if ($ConfigText -match "`"$escapedKey`"\s*:\s*false") {
        return "false"
    }
    return "__missing__"
}

$AssumeYes = $false
$ProbeMode = $false
$ModePromptConfirmed = $false
$ConfigOverride = ""

for ($i = 0; $i -lt $args.Length; $i++) {
    $token = [string]$args[$i]
    if ($token -match '^(-y|--yes)$') {
        $AssumeYes = $true
        continue
    }
    if ($token -eq "--probe") {
        $ProbeMode = $true
        continue
    }
    if ($token -eq "--config") {
        if ($i + 1 -ge $args.Length) {
            Write-Host "❌ --config 需要一个文件路径"
            exit 1
        }
        $ConfigOverride = Resolve-FullPath ([string]$args[$i + 1])
        $i++
        continue
    }
    if ($token -match '^--config=(.+)$') {
        $ConfigOverride = Resolve-FullPath $matches[1]
        continue
    }
}

if ($ProbeMode) {
    Write-Host "🛡️ 启动大麦安全探测脚本..."
} else {
    Write-Host "🎫 启动大麦抢票脚本..."
}

$androidHome = Find-AndroidHome
if (-not $androidHome) {
    Write-Host "❌ 未找到 Android SDK，请设置 ANDROID_HOME 环境变量"
    exit 1
}
$env:ANDROID_HOME = $androidHome
$env:ANDROID_SDK_ROOT = $androidHome

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mobileDir = Resolve-FullPath (Join-Path $scriptDir "..")
$rootDir = Resolve-FullPath (Join-Path $scriptDir "..\..")

$defaultConfigFile = Join-Path $mobileDir "config.jsonc"
if ($ConfigOverride) {
    $configFile = $ConfigOverride
} elseif ($env:HATICKETS_CONFIG_PATH -and $env:HATICKETS_CONFIG_PATH.Trim()) {
    $configFile = Resolve-FullPath $env:HATICKETS_CONFIG_PATH.Trim()
} else {
    $configFile = $defaultConfigFile
}

if (-not (Test-Path -LiteralPath $configFile -PathType Leaf)) {
    Write-Host "❌ 配置文件不存在: $configFile"
    Write-Host "   可先复制模板: cp mobile/config.example.jsonc mobile/config.jsonc"
    exit 1
}

Write-Host "✅ 配置文件存在: $configFile"
if ($configFile -ne $defaultConfigFile) {
    Write-Host "🧑‍💻 当前使用显式指定的开发者配置覆盖文件"
}

$adb = Get-AdbCommand $androidHome
$deviceOutput = & $adb devices 2>$null
$deviceLines = @($deviceOutput | Where-Object { $_ -match '^\S+\s+device$' })
if ($deviceLines.Count -lt 1) {
    Write-Host "❌ 未检测到已连接的 Android 设备"
    Write-Host "   请通过 USB 连接设备并开启 USB 调试模式"
    exit 1
}
Write-Host "✅ Android 设备连接正常"

$pythonBin = Get-PythonCommand $rootDir
if (-not $pythonBin) {
    Write-Host "❌ 未找到可用的 Python 环境"
    exit 1
}

$configText = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8
$currentProbeOnly = Get-ConfigFlag $configText "probe_only"
$currentIfCommitOrder = Get-ConfigFlag $configText "if_commit_order"

if ($ProbeMode) {
    $desiredProbeOnly = "true"
    $desiredIfCommitOrder = "false"
} else {
    $desiredProbeOnly = "false"
    $desiredIfCommitOrder = "true"
}

function Confirm-ModeSwitch([string]$Message) {
    if ($AssumeYes) {
        Write-Host "🤖 已启用 --yes，自动确认并继续"
        return $true
    }
    $reply = Read-Host "$Message (y/N)"
    if ($reply -match '^[Yy]$') {
        $script:ModePromptConfirmed = $true
        return $true
    }
    return $false
}

if (($currentProbeOnly -ne $desiredProbeOnly) -or ($currentIfCommitOrder -ne $desiredIfCommitOrder)) {
    Write-Host "========================================"
    if ($ProbeMode) {
        Write-Host "🛡️ 检测到当前配置不是安全探测模式"
        Write-Host "   当前配置: probe_only=$currentProbeOnly, if_commit_order=$currentIfCommitOrder"
        Write-Host "   即将改为: probe_only=true, if_commit_order=false"
        Write-Host "   这次运行会写回配置文件，然后开始安全探测"
        if (-not (Confirm-ModeSwitch "👉 是否立即切换到安全探测模式并继续？")) {
            Write-Host "❌ 已取消，配置文件未修改"
            exit 1
        }
    } else {
        Write-Host "🚨 检测到当前配置还不是正式抢票模式"
        Write-Host "   当前配置: probe_only=$currentProbeOnly, if_commit_order=$currentIfCommitOrder"
        Write-Host "   即将改为: probe_only=false, if_commit_order=true"
        Write-Host "   这次运行会写回配置文件，然后立即开始正式抢票"
        if (-not (Confirm-ModeSwitch "👉 是否立即切换到正式抢票模式并继续？")) {
            Write-Host "❌ 已取消，配置文件未修改"
            exit 1
        }
    }

    $previousPythonPath = $env:PYTHONPATH
    $env:HATICKETS_CONFIG_PATH = $configFile
    if ($previousPythonPath -and $previousPythonPath.Trim()) {
        $env:PYTHONPATH = "$rootDir;$previousPythonPath"
    } else {
        $env:PYTHONPATH = $rootDir
    }

    Push-Location $rootDir
    try {
        & $pythonBin -c "import sys; from mobile.config import update_runtime_mode; update_runtime_mode(sys.argv[1].lower()=='true', sys.argv[2].lower()=='true')" $desiredProbeOnly $desiredIfCommitOrder
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ 修改配置文件失败: $configFile"
            exit 1
        }
    } finally {
        Pop-Location
    }

    Write-Host "✅ 已写回配置文件: $configFile"
    Write-Host "   已更新为: probe_only=$desiredProbeOnly, if_commit_order=$desiredIfCommitOrder"
    Write-Host "========================================"
    $configText = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8
}

Write-Host "📋 当前配置:"
$summaryLines = Get-Content -LiteralPath $configFile -Encoding UTF8 | Where-Object { $_ -match '"(keyword|city|users)"' } | Select-Object -First 3
foreach ($line in $summaryLines) {
    Write-Host "   $line"
}

if ($configText -match '"probe_only"\s*:\s*true') {
    Write-Host "🛡️ 当前模式: 安全探测模式"
    Write-Host "   本次运行只会定位目标演出页，不会点击“立即购票/立即预订”"
} elseif ($configText -match '"if_commit_order"\s*:\s*false') {
    Write-Host "🧑‍💻 当前模式: 开发验证模式"
    Write-Host "   本次运行会走到确认页并勾选观演人，但不会点击“立即提交”；这是开发调试路径"
} else {
    Write-Host "🔥 当前模式: 正式提交模式"
    Write-Host "   本次运行会尝试提交订单，请再次确认配置"
}

if ($AssumeYes) {
    Write-Host "🤖 已启用 --yes，跳过交互确认"
} elseif ($ModePromptConfirmed) {
    Write-Host "✅ 已确认切换运行模式，继续执行"
} else {
    $reply = Read-Host "🤔 确认开始抢票？(y/N)"
    if ($reply -notmatch '^[Yy]$') {
        Write-Host "❌ 已取消"
        exit 1
    }
}

Push-Location $mobileDir
try {
    Write-Host "🚀 开始执行脚本..."
    Write-Host "   请确保："
    Write-Host "   1. 大麦APP已打开"
    Write-Host "   2. 大麦账号已保持登录"
    Write-Host "   3. 如果配置了 item_url + auto_navigate=true，可停留在首页"
    Write-Host "   4. 如果没有开启自动导航，请先手动进入演出详情页面"
    if ($ProbeMode) {
        Write-Host "   5. 当前命令已锁定为安全探测模式，不会提交订单"
    } else {
        Write-Host "   5. 当前命令已锁定为正式抢票模式，会尝试提交订单"
    }
    Write-Host ""

    $env:HATICKETS_CONFIG_PATH = $configFile
    $venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        & $venvPython "damai_app.py"
        exit $LASTEXITCODE
    }

    $poetry = Get-Command poetry -ErrorAction SilentlyContinue
    if ($poetry) {
        & $poetry.Path run python "damai_app.py"
        exit $LASTEXITCODE
    }

    Write-Host "❌ 未找到可用的 Python 环境"
    exit 1
} finally {
    Pop-Location
}

