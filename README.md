# svn-reviewboard

[English](#english) | [中文](#中文)

An Agent Skill for the **SVN + ReviewBoard** review loop: post SVN diffs to ReviewBoard with RBTools, then read comments, reply to reviewers, update the diff and close the review request.

Scripts are plain Python 3.7+ (stdlib only, plus the `rbt` CLI), work on Windows and Linux, and need no third-party Python packages.

## English

### What it does

| Script | Purpose |
| --- | --- |
| `scripts/rb_check_env.py` | Environment self-check: `svn`, `rbt`, SVN working copy, `.reviewboardrc` config (offline) |
| `scripts/rb_post.py` | Wraps `rbt post`: uncommitted changes, `--revisions 100:105`, `-I` for selected files, update an existing request |
| `scripts/rb_comments.py` | Fetch review comments (text / `--json` / open issues only) |
| `scripts/rb_reply.py` | Reply to a comment or a whole review, optionally `--resolve` / `--drop` the issue |

Typical loop: post → read comments → fix code and update with `-u` → reply to each comment and resolve → confirm Ship It → `rbt close`.

### Install

Drop the whole directory into your agent's skills folder:

```powershell
git clone https://github.com/yuylong/svn-reviewboard-skill.git $HOME\.trae-cn\skills\svn-reviewboard
```

The skill name comes from the `SKILL.md` frontmatter (`name: svn-reviewboard`); it triggers on intents like "post for review", "reply to comments", "ship it".

Requirements:

- `svn` client on `PATH` (TortoiseSVN with command line tools, or SlikSVN)
- RBTools: `pip install rbtools`

### Configure

Copy `assets/reviewboardrc` to the root of your SVN working copy as `.reviewboardrc` (scripts search upward from the current directory, then fall back to `~/.reviewboardrc`):

```python
REVIEWBOARD_URL = "https://reviewboard.example.com"
REPOSITORY = "my-repo"          # must match the repository name registered in ReviewBoard

API_TOKEN = "rbp_xxxxxxxx"      # recommended: ReviewBoard -> My Account -> API Tokens
# or
# USERNAME = "your-username"
# PASSWORD = "your-password"
```

Optional keys: `TARGET_PEOPLE`, `TARGET_GROUPS`, `BRANCH`, `DISABLE_SSL_VERIFICATION`.

### Usage

```powershell
# 0. environment check
python scripts/rb_check_env.py

# 1. post uncommitted changes
python scripts/rb_post.py --summary "Title" --description "Details" --target-people alice,bob

#    committed revisions / selected files / update an existing request
python scripts/rb_post.py --revisions 100:105 --summary "..."
python scripts/rb_post.py --summary "..." -I src/foo.c
python scripts/rb_post.py -r 1234 -u

# 2. read comments
python scripts/rb_comments.py -r 1234 --open

# 3. reply and close the issue
python scripts/rb_reply.py -r 1234 --comment 881 --message "Fixed in r2" --resolve
```

Every script supports `--help`; `rb_post.py` also has `--diff-only`, `--dry-run`, `--open`, `--debug`.

### Layout

```
SKILL.md                         # skill definition and full usage (read by the agent)
scripts/                         # rb_check_env / rb_post / rb_comments / rb_reply / rb_common
assets/reviewboardrc             # config template
references/reviewboard-api.md    # ReviewBoard REST endpoints used by the scripts
references/troubleshooting.md    # 401/403, REPOSITORY mismatch, SSL/proxy, encoding issues
```

### Notes

- Files in `?` state from `svn status` are not in the diff — `svn add` them first
- For changelists, filter with `-I`, listing files via `svn status --cl <name>`
- SVN only; for Git projects use RBTools' native git support

### License

BSD 3-Clause, see [LICENSE](LICENSE).

## 中文

一个用于 **SVN + ReviewBoard** 提审闭环的 Agent Skill：用 RBTools 把 SVN diff 提到 ReviewBoard，再处理查看意见、逐条回复、更新 diff、关闭评审。

脚本是纯 Python 3.7+（仅标准库 + `rbt` 命令行），Windows / Linux 通用，不依赖任何第三方 Python 包。

### 能力

| 脚本 | 作用 |
| --- | --- |
| `scripts/rb_check_env.py` | 环境自检：svn / rbt / 是否 SVN 工作副本 / `.reviewboardrc` 配置（离线可跑） |
| `scripts/rb_post.py` | 封装 `rbt post`：未提交改动、`--revisions 100:105`、`-I` 只传部分文件、更新已有评审单 |
| `scripts/rb_comments.py` | 拉取评审意见（文本 / `--json` / 只看 open issue） |
| `scripts/rb_reply.py` | 回复评论或整条 review，可顺带 `--resolve` / `--drop` 关闭 issue |

标准闭环：提审 → 看意见 → 改代码 `-u` 更新 diff → 逐条回复并 resolve → 确认 Ship It → `rbt close`。

### 安装

把整个目录放进宿主工具的 skills 目录即可，例如：

```powershell
# Trae / Claude Code 全局技能目录
git clone https://github.com/yuylong/svn-reviewboard-skill.git $HOME\.trae-cn\skills\svn-reviewboard
```

技能名由 `SKILL.md` 的 frontmatter 决定（`name: svn-reviewboard`），出现「提审 / 上传评审 / 回复评论 / 关闭评审 / ship it」等意图时触发。

需要宿主已具备：

- `svn` 客户端（TortoiseSVN 勾选 command line tools，或 SlikSVN）在 PATH 中
- RBTools：`pip install rbtools`

### 配置

把 `assets/reviewboardrc` 复制到 SVN 工作副本根目录并改名为 `.reviewboardrc`（脚本会从当前目录逐级向上查找，找不到则回退 `~/.reviewboardrc`）：

```python
REVIEWBOARD_URL = "https://reviewboard.example.com"
REPOSITORY = "my-repo"          # 必须与 RB 后台登记的仓库完全一致

API_TOKEN = "rbp_xxxxxxxx"      # 推荐：RB 网页 My Account -> API Tokens
# 或
# USERNAME = "your-username"
# PASSWORD = "your-password"
```

可选键：`TARGET_PEOPLE`、`TARGET_GROUPS`、`BRANCH`、`DISABLE_SSL_VERIFICATION`。

### 使用

```powershell
# 0. 环境自检
python scripts/rb_check_env.py

# 1. 提审（当前未提交改动）
python scripts/rb_post.py --summary "标题" --description "说明" --target-people alice,bob

#    已提交的版本区间 / 只传部分文件 / 更新已有评审单
python scripts/rb_post.py --revisions 100:105 --summary "..."
python scripts/rb_post.py --summary "..." -I src/foo.c
python scripts/rb_post.py -r 1234 -u

# 2. 看意见
python scripts/rb_comments.py -r 1234 --open

# 3. 回复并关闭 issue
python scripts/rb_reply.py -r 1234 --comment 881 --message "已在 r2 修复" --resolve
```

所有脚本都支持 `--help`；`rb_post.py` 另有 `--diff-only`、`--dry-run`、`--open`、`--debug`。

### 目录结构

```
SKILL.md                     # 技能定义与完整用法（Agent 读取）
scripts/                     # rb_check_env / rb_post / rb_comments / rb_reply / rb_common
assets/reviewboardrc         # 配置模板
references/reviewboard-api.md    # 脚本用到的 ReviewBoard REST API
references/troubleshooting.md    # 401/403、REPOSITORY 不匹配、SSL/代理、中文乱码等排错
```

### 说明

- 新文件在 `svn status` 里是 `?` 时不会进 diff，提审前请先 `svn add`
- changelist 场景用 `-I` 按文件过滤，文件列表来自 `svn status --cl 名字`
- 只面向 SVN；Git 项目请直接用 RBTools 的 git 支持

### License

BSD 3-Clause，见 [LICENSE](LICENSE)。
