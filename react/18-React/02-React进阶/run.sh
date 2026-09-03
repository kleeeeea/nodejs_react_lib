#!/usr/bin/env bash
# React 进阶示例一键启动脚本。章节挑选与 src/ 准备的逻辑都在 prepare.py 里。
#
# 用法：
#   ./run.sh                     用当前 src/ 直接启动开发服务器
#   ./run.sh -l                  列出所有可运行的章节
#   ./run.sh 12-Redux/04         把该章节装进 src/ 再启动（原 src 会先备份）
#   ./run.sh 05 --port 3001      模糊匹配章节名，并指定端口
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

command -v node >/dev/null 2>&1 || { echo "[run] 错误：未找到 node。" >&2; exit 1; }
PYTHON="${PYTHON:-python3}"
command -v "${PYTHON}" >/dev/null 2>&1 || { echo "[run] 错误：未找到 ${PYTHON}。" >&2; exit 1; }
if command -v pnpm >/dev/null 2>&1; then PM=pnpm
elif command -v npm >/dev/null 2>&1; then PM=npm
else echo "[run] 错误：未找到 pnpm 或 npm。" >&2; exit 1; fi

if [[ ! -d node_modules ]]; then
  echo "[run] 首次运行，安装依赖（${PM}）…"
  "${PM}" install
fi

# prepare.py 的日志走 stderr，stdout 只回一行 port=xxx；退出码 10 = 无需启动服务。
set +e
PLAN="$("${PYTHON}" prepare.py --pm "${PM}" "$@")"
STATUS=$?
set -e
[[ ${STATUS} -eq 10 ]] && exit 0
[[ ${STATUS} -eq 0 ]] || exit ${STATUS}
PORT="${PLAN#port=}"

echo "[run] 启动开发服务器（${PM} run dev）…"
if [[ -z "${PORT}" ]]; then
  exec "${PM}" run dev
elif [[ "${PM}" == "pnpm" ]]; then
  # pnpm 会把 `--` 原样传给 vite（vite 忽略其后的参数），npm 则必须有 `--`。
  exec pnpm run dev --port "${PORT}" --strictPort
else
  exec "${PM}" run dev -- --port "${PORT}" --strictPort
fi
