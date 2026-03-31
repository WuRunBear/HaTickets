#!/bin/bash
# 大麦抢票 - 抢票启动脚本
# 使用方法: ./start_ticket_grabbing.sh [--yes] [--config mobile/config.local.jsonc]

ASSUME_YES=false
CONFIG_OVERRIDE=""

resolve_path() {
    local target="$1"
    if [[ "$target" = /* ]]; then
        printf '%s\n' "$target"
    else
        printf '%s\n' "$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes)
            ASSUME_YES=true
            shift
            ;;
        --config)
            if [ -z "$2" ]; then
                echo "❌ --config 需要一个文件路径"
                exit 1
            fi
            CONFIG_OVERRIDE="$(resolve_path "$2")"
            shift 2
            ;;
        --config=*)
            CONFIG_OVERRIDE="$(resolve_path "${1#*=}")"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "🎫 启动大麦抢票脚本..."

# 设置Android环境变量（优先使用已有环境变量，否则自动检测常见路径）
if [ -z "$ANDROID_HOME" ]; then
    if [ -d "$HOME/Library/Android/sdk" ]; then
        export ANDROID_HOME="$HOME/Library/Android/sdk"
    elif [ -d "$HOME/Android/Sdk" ]; then
        export ANDROID_HOME="$HOME/Android/Sdk"
    elif [ -d "/opt/android-sdk" ]; then
        export ANDROID_HOME="/opt/android-sdk"
    else
        echo "❌ 未找到 Android SDK，请设置 ANDROID_HOME 环境变量"
        exit 1
    fi
fi
export ANDROID_SDK_ROOT="$ANDROID_HOME"

# 检查Appium服务器是否运行
if ! curl -s http://127.0.0.1:4723/status > /dev/null; then
    echo "❌ Appium服务器未运行"
    echo "   请先运行: ./start_appium.sh"
    exit 1
fi

echo "✅ Appium服务器运行正常"

# 解析目录，确保从任意目录执行都能找到配置文件与虚拟环境
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEFAULT_CONFIG_FILE="$MOBILE_DIR/config.jsonc"
if [ -n "$CONFIG_OVERRIDE" ]; then
    CONFIG_FILE="$CONFIG_OVERRIDE"
elif [ -n "$HATICKETS_CONFIG_PATH" ]; then
    CONFIG_FILE="$(resolve_path "$HATICKETS_CONFIG_PATH")"
else
    CONFIG_FILE="$DEFAULT_CONFIG_FILE"
fi

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    echo "   可先复制模板: cp mobile/config.example.jsonc mobile/config.jsonc"
    exit 1
fi

echo "✅ 配置文件存在: $CONFIG_FILE"
if [ "$CONFIG_FILE" != "$DEFAULT_CONFIG_FILE" ]; then
    echo "🧑‍💻 当前使用显式指定的开发者配置覆盖文件"
fi

# 显示当前配置
echo "📋 当前配置:"
echo "   $(cat "$CONFIG_FILE" | grep -E '"keyword"|"city"|"users"' | head -3)"

if grep -Eq '"probe_only"[[:space:]]*:[[:space:]]*true' "$CONFIG_FILE"; then
    echo "🛡️ 当前模式: 安全探测模式"
    echo "   本次运行只会定位目标演出页，不会点击“立即购票/立即预订”"
elif grep -Eq '"if_commit_order"[[:space:]]*:[[:space:]]*false' "$CONFIG_FILE"; then
    echo "🧑‍💻 当前模式: 开发验证模式"
    echo "   本次运行不会提交订单；这是开发调试路径，不属于 README 的普通用户流程"
else
    echo "🔥 当前模式: 正式提交模式"
    echo "   本次运行会尝试提交订单，请再次确认配置"
fi

# 确认是否继续
if [ "$ASSUME_YES" = true ]; then
    echo "🤖 已启用 --yes，跳过交互确认"
else
    read -p "🤔 确认开始抢票？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 已取消"
        exit 1
    fi
fi

# 进入脚本目录
cd "$MOBILE_DIR"

echo "🚀 开始执行脚本..."
echo "   请确保："
echo "   1. 大麦APP已打开"
echo "   2. 大麦账号已保持登录"
echo "   3. 如果配置了 item_url + auto_navigate=true，可停留在首页"
echo "   4. 如果没有开启自动导航，请先手动进入演出详情页面"
echo "   5. 当前命令不会强制正式抢票，实际行为以 probe_only / if_commit_order 配置为准"
echo ""

# 运行抢票脚本（优先使用项目 .venv，其次使用 Poetry）
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    HATICKETS_CONFIG_PATH="$CONFIG_FILE" "$ROOT_DIR/.venv/bin/python" damai_app.py
elif command -v poetry &> /dev/null; then
    HATICKETS_CONFIG_PATH="$CONFIG_FILE" poetry run python damai_app.py
else
    echo "❌ 未找到可用的 Python 环境"
    echo "   请先安装依赖："
    echo "   1) 使用 Poetry: python3 -m pip install --user poetry"
    echo "      然后运行: poetry install"
    echo "   2) 或在 .venv 中安装: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi
