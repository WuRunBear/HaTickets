#!/bin/bash
# 使用自然语言提示词驱动大麦 mobile 流程
# 用法:
#   ./mobile/scripts/run_from_prompt.sh "帮张志涛抢一张 4 月 6 号张杰的演唱会门票，内场"
#   ./mobile/scripts/run_from_prompt.sh --mode probe --yes "帮张志涛抢一张 4 月 6 号张杰的演唱会门票，内场"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    "$REPO_ROOT/.venv/bin/python" mobile/prompt_runner.py "$@"
elif command -v poetry >/dev/null 2>&1; then
    poetry run python mobile/prompt_runner.py "$@"
elif command -v python3 >/dev/null 2>&1; then
    python3 mobile/prompt_runner.py "$@"
elif command -v python >/dev/null 2>&1; then
    python mobile/prompt_runner.py "$@"
else
    echo "❌ 未找到可用的 Python 环境"
    exit 1
fi
