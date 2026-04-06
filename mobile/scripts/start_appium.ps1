$ErrorActionPreference = "Stop"

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

Write-Host "🚀 启动大麦抢票环境..."

$androidHome = Find-AndroidHome
if (-not $androidHome) {
    Write-Host "❌ 未找到 Android SDK，请设置 ANDROID_HOME 环境变量"
    exit 1
}
$env:ANDROID_HOME = $androidHome
$env:ANDROID_SDK_ROOT = $androidHome

Write-Host "✅ 环境变量已设置"
Write-Host "   ANDROID_HOME: $env:ANDROID_HOME"
Write-Host "   ANDROID_SDK_ROOT: $env:ANDROID_SDK_ROOT"

$adb = Get-AdbCommand $androidHome

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "❌ 未找到 Node.js，请先安装 Node.js"
    exit 1
}
$nodeVersion = & $node.Path --version
Write-Host "📦 Node.js版本: $nodeVersion"

$appium = Get-Command appium -ErrorAction SilentlyContinue
if (-not $appium) {
    Write-Host "❌ Appium未安装，请先安装Appium"
    Write-Host "   运行: npm install -g appium"
    exit 1
}

Write-Host "📱 检查Android设备..."
$deviceOutput = & $adb devices 2>$null
$deviceLines = @($deviceOutput | Where-Object { $_ -match '^\S+\s+device$' })
if ($deviceLines.Count -eq 0) {
    Write-Host "⚠️  未检测到Android设备"
    Write-Host "   请启动模拟器或连接真机"
    exit 1
}
Write-Host "✅ 检测到 $($deviceLines.Count) 个Android设备"

$packages = & $adb shell pm list packages 2>$null
if (-not ($packages | Where-Object { $_ -match 'cn\.damai' })) {
    Write-Host "⚠️  大麦APP未安装"
    Write-Host "   请在设备上安装大麦APP"
    exit 1
}
Write-Host "✅ 大麦APP已安装"

Write-Host "🚀 启动Appium服务器..."
Write-Host "   服务器地址: http://127.0.0.1:4723"
Write-Host "   按 Ctrl+C 停止服务器"
Write-Host ""

& $appium.Path --port 4723
exit $LASTEXITCODE
