#!/usr/bin/env python3
"""为 run.sh 准备 src/ 目录：列章节、切章节、查缺包。

这个目录是一个 Vite 工程，index.html 固定加载 /src/main.jsx，所以要看哪一章，
就得先把那一章的代码搬进根目录 src/。这里负责搬运，run.sh 只管装依赖和起服务。

与 run.sh 的约定：
  * 人看的日志一律写 stderr；stdout 只输出一行 `port=<端口>` 供 run.sh 读取。
  * 退出码 10 表示「该做的都做完了，不用启动服务」（--list / --help）。
"""

import argparse
import os
import re
import shutil
import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
BACKUP_ROOT = ROOT / ".src-backup"
PRUNE_DIRS = {"node_modules", ".src-backup", ".git", "dist", "build"}
CODE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
# from 'x' / require('x') / import 'x'（副作用导入，比如 import 'antd/dist/antd.css'）
IMPORT_RE = re.compile(r"""(?:from\s*|require\(\s*|import\s+)['"]([^'"]+)['"]""")


def log(message):
    print(f"[prepare] {message}", file=sys.stderr)


def fail(message):
    log(f"错误：{message}")
    sys.exit(1)


def list_chapters():
    """章节 = 含入口文件的目录。

    入口通常是 main.jsx；早几章沿用 CRA 的 index.js，只有同目录还有 App.js(x)
    时才算入口，否则组件目录里的 index.js 也会被误判成章节。
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        current = Path(dirpath)
        if current == ROOT or current == SRC or SRC in current.parents:
            continue
        names = set(filenames)
        if "main.jsx" in names:
            found.append(current)
        elif "index.js" in names and names & {"App.js", "App.jsx"}:
            found.append(current)
    return sorted(path.relative_to(ROOT).as_posix() for path in found)


def resolve_chapter(query):
    chapters = list_chapters()
    matches = [name for name in chapters if query in name]
    if not matches:
        log(f"没有匹配「{query}」的章节，可选的是：")
        for name in chapters:
            print(f"  {name}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        log(f"「{query}」匹配到多个章节，请写得更具体：")
        for name in matches:
            print(f"  {name}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def load_chapter(name):
    """把章节复制进 src/，原 src/ 先整份备份，绝不静默丢代码。"""
    if SRC.exists():
        BACKUP_ROOT.mkdir(exist_ok=True)
        backup = BACKUP_ROOT / f"src-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copytree(SRC, backup)
        log(f"已备份原 src/ 到 {backup.relative_to(ROOT)}")
        shutil.rmtree(SRC)
    shutil.copytree(ROOT / name, SRC)
    # index.html 固定加载 /src/main.jsx，给 CRA 风格的章节补一个入口别名。
    if not (SRC / "main.jsx").exists() and (SRC / "index.js").exists():
        shutil.copy2(SRC / "index.js", SRC / "main.jsx")
        log("该章入口是 index.js，已复制一份为 main.jsx 供 Vite 使用。")
    log(f"已载入章节：{name} -> src/")


def warn_missing_deps(pm):
    """章节可能 import 了 package.json 没装的包，提前提示，免得白屏了才去翻控制台。"""
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    declared = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))

    used = set()
    for path in SRC.rglob("*"):
        if path.suffix not in CODE_SUFFIXES or not path.is_file():
            continue
        for spec in IMPORT_RE.findall(path.read_text(encoding="utf-8", errors="ignore")):
            if spec.startswith((".", "/")):
                continue
            parts = spec.split("/")
            used.add("/".join(parts[:2]) if spec.startswith("@") else parts[0])

    missing = sorted(used - declared)
    if missing:
        log(f"提示：本章用到但 package.json 里没有的包：{' '.join(missing)}")
        log(f"      需要的话先装：{pm} add {' '.join(missing)}")


def main():
    parser = argparse.ArgumentParser(
        prog="./run.sh", add_help=False, description="启动 React 进阶示例：不带参数用当前 src/，带章节名则先切换章节"
    )
    parser.add_argument("chapter", nargs="?", help="章节名，支持子串模糊匹配，例如 12-Redux/04")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有可运行的章节")
    parser.add_argument("-p", "--port", default="", help="开发服务器端口（默认用 vite.config.js 里的 3000）")
    parser.add_argument("--pm", default="pnpm", help="包管理器名，仅用于提示信息")
    parser.add_argument("-h", "--help", action="store_true", help="显示帮助")
    args = parser.parse_args()

    if args.help:
        parser.print_help(sys.stderr)
        sys.exit(10)
    if args.list:
        for name in list_chapters():
            print(name, file=sys.stderr)
        sys.exit(10)

    if args.chapter:
        load_chapter(resolve_chapter(args.chapter.rstrip("/")))

    if not (SRC / "main.jsx").exists():
        fail("src/main.jsx 不存在，Vite 没有入口。先用 ./run.sh <章节> 载入一章（./run.sh -l 看列表）。")

    warn_missing_deps(args.pm)
    print(f"port={args.port}")


if __name__ == "__main__":
    main()
