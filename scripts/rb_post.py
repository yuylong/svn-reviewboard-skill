#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封装 rbt post，把 SVN diff 提交到 ReviewBoard。

模式：
- 默认：上传当前工作副本未提交的改动；可用 -I 文件 只传部分文件
- --revisions 100:105：上传已提交的版本区间（SVN 原生语法，单版本直接写 100）
- -r <ID> [-u]：更新已有评审单

配置：向上查找 .reviewboardrc（同 RBTools 约定），
TARGET_PEOPLE / TARGET_GROUPS / BRANCH 作为对应参数的默认值。
"""
import argparse
import locale
import re
import shutil
import subprocess
import sys

from rb_common import find_config, load_config

REVISION_RE = re.compile(r"^\d+(:\d+)?$")
RR_ID_RE = re.compile(r"Review request #(\d+)")
RR_URL_RE = re.compile(r"https?://\S+?/r/\d+/?\S*")


def decode_output(data):
    for enc in (locale.getpreferredencoding(False), "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", "replace")


def parse_args():
    ap = argparse.ArgumentParser(
        description="rbt post 的 SVN 友好封装（未提交改动 / 版本区间 / 更新评审单）")
    ap.add_argument("--summary", help="评审标题")
    ap.add_argument("--description", help="评审说明")
    ap.add_argument("--target-people", help="评审人，逗号分隔（默认取配置 TARGET_PEOPLE）")
    ap.add_argument("--target-groups", help="评审组，逗号分隔（默认取配置 TARGET_GROUPS）")
    ap.add_argument("--bugs-closed", help="关联 bug 单号，逗号分隔")
    ap.add_argument("--branch", help="分支名（默认取配置 BRANCH）")
    ap.add_argument("--revisions", help="已提交版本，如 100:105 或 100")
    ap.add_argument("--repository", help="覆盖默认仓库（默认取配置 REPOSITORY；都不设则 rbt 自动匹配）")
    ap.add_argument("-r", "--review-id", help="已有评审单 ID")
    ap.add_argument("-u", "--update", action="store_true", help="更新已有评审单")
    ap.add_argument("-I", "--include", action="append", default=[], metavar="FILE",
                    help="只上传指定文件，可重复（changelist 场景配合 svn status --cl）")
    ap.add_argument("--diff-only", nargs="?", const="", default=None, metavar="OUTFILE",
                    help="只生成 diff 不提单（可选输出文件名）")
    ap.add_argument("--open", action="store_true", help="上传后自动打开浏览器")
    ap.add_argument("--dry-run", action="store_true", help="只打印将执行的命令")
    ap.add_argument("--debug", action="store_true", help="透传 rbt 的 --debug")
    return ap.parse_args()


def svn_status_unversioned():
    try:
        p = subprocess.run(["svn", "status"], capture_output=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    out = decode_output(p.stdout or b"")
    return [line[8:].strip() for line in out.splitlines() if line.startswith("?")]


def main():
    args = parse_args()
    if args.revisions and not REVISION_RE.match(args.revisions):
        print(f"[错误] --revisions 只支持 100 或 100:105 形式，收到：{args.revisions}")
        return 2
    if args.revisions and (args.review_id or args.update):
        print("[错误] --revisions 与 -r/-u 不能同时用")
        return 2

    cfg_path = find_config()
    cfg = load_config(cfg_path) if cfg_path else {}
    if not cfg.get("REVIEWBOARD_URL") and not args.dry_run:
        print("[警告] 未找到 .reviewboardrc 或缺少 REVIEWBOARD_URL，rbt 很可能失败（先跑 rb_check_env.py）")

    rbt = shutil.which("rbt")
    if not rbt and not args.dry_run:
        print("[错误] rbt 不可用，请先 pip install rbtools")
        return 2
    rbt = rbt or "rbt"

    if args.revisions is None and not args.diff_only:
        unversioned = svn_status_unversioned()
        if unversioned:
            print("[提示] 以下新文件未纳入 svn 管理，diff 不会包含它们（先 svn add）：")
            for f in unversioned:
                print(f"   ? {f}")

    cmd = [rbt, "post"]
    if args.debug:
        cmd.append("--debug")
    if args.summary:
        cmd += ["--summary", args.summary]
    if args.description:
        cmd += ["--description", args.description]
    people = args.target_people or ",".join(cfg.get("TARGET_PEOPLE") or [])
    if people:
        cmd += ["--target-people", people]
    groups = args.target_groups or ",".join(cfg.get("TARGET_GROUPS") or [])
    if groups:
        cmd += ["--target-groups", groups]
    if args.bugs_closed:
        cmd += ["--bugs-closed", args.bugs_closed]
    branch = args.branch or cfg.get("BRANCH")
    if branch:
        cmd += ["--branch", str(branch)]
    repository = args.repository or cfg.get("REPOSITORY")
    if repository:
        cmd += ["--repository", str(repository)]
    if args.review_id:
        cmd += ["-r", str(args.review_id)]
    if args.update:
        cmd.append("-u")
    for f in args.include:
        cmd += ["-I", f]
    if args.diff_only is not None:
        cmd.append("--diff-only")
        if args.diff_only:
            cmd.append(args.diff_only)
    if args.open:
        cmd.append("--open")
    if args.revisions:
        cmd.append(args.revisions)

    shown = " ".join(cmd)
    if args.dry_run:
        print("将执行:\n  " + shown)
        return 0

    print("执行:", shown)
    try:
        p = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        print("[错误] 无法启动 rbt")
        return 2
    out = decode_output(p.stdout or b"") + decode_output(p.stderr or b"")
    if out.strip():
        sys.stdout.write(out)
    if p.returncode != 0:
        print(f"[失败] rbt post 退出码 {p.returncode}")
        print("常见原因见 skill 的 references/troubleshooting.md（认证/REPOSITORY 不匹配/网络）")
        return p.returncode

    ids = RR_ID_RE.findall(out)
    urls = RR_URL_RE.findall(out)
    if ids:
        print(f"\n[完成] Review Request #{ids[-1]}")
    if urls:
        print("[完成] URL:", urls[-1])
    print("后续: 查意见 python rb_comments.py -r <ID>；更新 python rb_post.py -r <ID> -u")
    return 0


if __name__ == "__main__":
    sys.exit(main())
