#!/bin/bash
# 从当前抢票界面出发，安全压测最后热路径
# 使用方法: ./mobile/scripts/benchmark_hot_path.sh [--config mobile/config.local.jsonc] [--runs 5] [--price 580元] [--price-index 2] [--city 成都] [--date 04.18] [--json]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEFAULT_CONFIG_FILE="$REPO_ROOT/mobile/config.jsonc"
CONFIG_OVERRIDE=""

resolve_path() {
    local target="$1"
    if [[ "$target" = /* ]]; then
        printf '%s\n' "$target"
    else
        printf '%s\n' "$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"
    fi
}

ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
    case "${ARGS[$i]}" in
        --config)
            next_index=$((i + 1))
            if [ $next_index -ge ${#ARGS[@]} ]; then
                echo "❌ --config 需要一个文件路径"
                exit 1
            fi
            CONFIG_OVERRIDE="$(resolve_path "${ARGS[$next_index]}")"
            ;;
        --config=*)
            CONFIG_OVERRIDE="$(resolve_path "${ARGS[$i]#*=}")"
            ;;
    esac
done

if [ -n "$CONFIG_OVERRIDE" ]; then
    CONFIG_FILE="$CONFIG_OVERRIDE"
elif [ -n "$HATICKETS_CONFIG_PATH" ]; then
    CONFIG_FILE="$(resolve_path "$HATICKETS_CONFIG_PATH")"
else
    CONFIG_FILE="$DEFAULT_CONFIG_FILE"
fi

if ! curl -s http://127.0.0.1:4723/status > /dev/null; then
    echo "❌ Appium服务器未运行"
    echo "   请先运行: ./mobile/scripts/start_appium.sh"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    echo "   可先复制模板: cp mobile/config.example.jsonc mobile/config.jsonc"
    exit 1
fi

cd "$REPO_ROOT"

echo "⏱️  开始热路径压测..."
echo "   请确保手机已经停在目标演出的详情页或票档页"
echo "   当前配置文件: $CONFIG_FILE"
echo "   本脚本会强制使用安全模式: if_commit_order=false, auto_navigate=false, rush_mode=true"
echo ""

HATICKETS_CONFIG_PATH="$CONFIG_FILE" poetry run python mobile/hot_path_benchmark.py "$@"
