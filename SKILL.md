---
name: svn-reviewboard
description: Post SVN diffs to ReviewBoard via RBTools and handle the review loop — view comments, reply to reviewers, update diffs and close review requests. Use when the user says 提审, 上传评审, 提交评审, 回复评论, 看评审意见, 关闭评审, ship it, or wants a code review posted to ReviewBoard. Not for Git-based reviews.
---

# SVN ReviewBoard 提审与评审互动

用 RBTools 把 SVN diff 提交到 ReviewBoard，并处理评审闭环：查看意见、回复评论、更新 diff、关闭评审。脚本在 `scripts/`，均在 Windows/Linux 下用系统 Python（3.7+）运行，无第三方依赖；先跑 `python <脚本> --help` 看完整参数。

## 第 0 步：环境自检（任何操作前先跑一次）

```powershell
python scripts/rb_check_env.py
```

不访问服务器，离线可跑。检查项：svn 客户端、RBTools（缺失则 `pip install rbtools`）、当前目录是否 SVN 工作副本、`.reviewboardrc` 是否存在及关键字段。

配置缺失时：把 `assets/reviewboardrc` 复制到 SVN 仓库根目录改名 `.reviewboardrc`，让用户填写：
- `REVIEWBOARD_URL`（必填）
- `REPOSITORY`（强烈建议填，值必须与 RB 后台登记的仓库完全一致）
- 认证：`API_TOKEN`（推荐，RB 网页 My Account -> API Tokens 生成）或 `USERNAME` + `PASSWORD`

脚本从当前目录向上查找 `.reviewboardrc`，找不到回退 `~/.reviewboardrc`；所有脚本与 rbt 共用这一份配置。

## 提审（scripts/rb_post.py，封装 rbt post）

```powershell
# 未提交的本地改动（最常用）
python scripts/rb_post.py --summary "标题" --description "说明" --target-people alice,bob

# 只传部分文件
python scripts/rb_post.py --summary "..." -I src/foo.c -I data/bar.png

# 指定/覆盖仓库（默认取配置 REPOSITORY）
python scripts/rb_post.py --summary "..." --repository SEEDv3

# 已提交的版本区间（SVN 原生语法，单版本直接写 100）
python scripts/rb_post.py --revisions 100:105 --summary "..."

# 更新已有评审单（改完代码后重新上传）
python scripts/rb_post.py -r 1234 -u

# 只生成 diff 预览不提单；--dry-run 只打印命令不执行
python scripts/rb_post.py --diff-only
python scripts/rb_post.py --dry-run --summary "..."
```

要点：
- 上传前脚本会跑 `svn status`：`?` 状态的新文件不会进 diff，先提醒用户 `svn add`（二进制文件同理）
- changelist 需求：用 `-I` 按文件过滤，文件列表来自 `svn status --cl 名字`
- 成功后脚本解析出 review request ID 和 URL，必须报告给用户
- `--open` 提审后自动开浏览器；`--debug` 透传 rbt 排错

## 查看评审意见（scripts/rb_comments.py）

```powershell
python scripts/rb_comments.py -r 1234          # 全部意见
python scripts/rb_comments.py -r 1234 --open   # 只看 open issue
python scripts/rb_comments.py -r 1234 --json   # 结构化输出
python scripts/rb_comments.py -r 1234 --server https://rb.example.com   # 临时覆盖服务器
```

输出每条意见的：review ID、评论 ID、评审人、文件/行号、内容、issue 状态（open/resolved）、是否 Ship It。回复时用**评论 ID**（comment 后面的数字），不是显示序号。

## 回复评论（scripts/rb_reply.py）

```powershell
# 回复某条评论，并顺带把 issue 标记为已解决（或 --drop 放弃）
python scripts/rb_reply.py -r 1234 --comment 881 --message "已在 r2 修复" --resolve

# 对某条 review 顶层回复
python scripts/rb_reply.py -r 1234 --review 55 --message "收到，已处理"

# 对整个评审单发顶层评论
python scripts/rb_reply.py -r 1234 --message "已按意见更新 diff"
```

回复会立即发布。`--resolve/--drop` 只对开了 issue 的 diff/general 评论有效。

## 评审闭环（标准流程，按需逐步执行）

1. 提审：`rb_post.py` → 把 ID 和 URL 报告给用户
2. 用户说"看看意见/回复一下" → `rb_comments.py -r <ID>` 汇报
3. 用户改完代码 → `rb_post.py -r <ID> -u` 更新 diff
4. `rb_reply.py --comment <cid> --message "已在新 diff 中修复" --resolve` 逐条回复
5. 确认 Ship It：`rb_comments.py -r <ID>`（看 ship_it 标记）
6. 关闭：`rbt close <ID>`（作废用 `rbt close <ID> --close-type discarded`）

查自己发出的评审单：`rbt status`。

## 排错

401/403 认证失败、REPOSITORY 不匹配、SSL/代理、中文乱码等，先查 `references/troubleshooting.md`；脚本用到的 API 端点在 `references/reviewboard-api.md`。
