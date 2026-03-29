#!/bin/bash
# 使用自然语言提示词驱动大麦 mobile 流程
# 用法:
#   ./mobile/scripts/run_from_prompt.sh "帮我抢一张 4 月 6 号张杰的演唱会门票，内场"
#   ./mobile/scripts/run_from_prompt.sh --mode probe --yes "帮我抢一张 4 月 6 号张杰的演唱会门票，内场"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
poetry run python mobile/prompt_runner.py "$@"
