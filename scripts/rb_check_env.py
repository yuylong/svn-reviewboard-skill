#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境与配置自检：svn / rbt / SVN 工作副本 / .reviewboardrc。

用法：python rb_check_env.py
不访问 ReviewBoard 服务器，可离线运行。退出码 0 = 就绪。
"""
import subprocess
import sys

from rb_common import find_config, load_config, mask


def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return None, "", f"找不到命令 {cmd[0]}"
    except subprocess.TimeoutExpired:
        return None, "", "命令超时"


def main():
    problems = []
    print("== svn-reviewboard 环境检查 ==\n")

    code, out, _ = run(["svn", "--version", "--quiet"])
    if code == 0:
        print(f"[OK]   svn 客户端: {out or '(版本号未知)'}")
    else:
        problems.append("svn 不可用，请安装 TortoiseSVN（勾选 command line tools）或 SlikSVN 并加入 PATH")

    code, out, _ = run(["rbt", "--version"])
    if code == 0:
        print(f"[OK]   RBTools: {out}")
    else:
        problems.append("rbt 不可用，请安装: pip install rbtools")

    print(f"[OK]   Python: {sys.version.split()[0]}")

    code, out, err = run(["svn", "info"])
    if code == 0:
        url = ""
        for line in out.splitlines():
            if line.startswith("URL:"):
                url = line[4:].strip()
                break
        print(f"[OK]   当前目录是 SVN 工作副本: {url or '(未解析到 URL)'}")
    else:
        first = err.splitlines()[0] if err else "未知原因"
        problems.append(f"当前目录不是 SVN 工作副本（svn info: {first}）")

    cfg_path = find_config()
    if not cfg_path:
        problems.append("未找到 .reviewboardrc（复制 assets/reviewboardrc 到仓库根目录改名，或放到用户主目录）")
    else:
        try:
            cfg = load_config(cfg_path)
        except Exception as e:
            problems.append(f"解析 {cfg_path} 失败: {e}")
        else:
            print(f"[OK]   配置文件: {cfg_path}")
            print(f"       REVIEWBOARD_URL = {cfg.get('REVIEWBOARD_URL', '(缺少!)')}")
            print(f"       REPOSITORY      = {cfg.get('REPOSITORY', '(未配置，rbt 将自动匹配，可能匹配错)')}")
            print(f"       认证            = API_TOKEN({mask(cfg.get('API_TOKEN'))})"
                  f" / 密码({mask(cfg.get('PASSWORD'))})")
            if not cfg.get("REVIEWBOARD_URL"):
                problems.append("配置里缺少 REVIEWBOARD_URL")
            if not cfg.get("API_TOKEN") and not (cfg.get("USERNAME") and cfg.get("PASSWORD")):
                problems.append("缺少认证信息：配置 API_TOKEN（推荐）或 USERNAME+PASSWORD")

    print()
    if problems:
        print("需要处理的问题:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("环境就绪，可以提审。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
