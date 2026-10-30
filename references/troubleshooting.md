# 常见问题排查

## rbt post（提审/更新）

- `There is already a review request for this commit` → 该版本区间已提过审，用 `rb_post.py -r <已有ID> -u` 更新，不要新建
- `does not match any registered repositories` / 仓库匹配失败 → `.reviewboardrc` 的 `REPOSITORY` 必须与 RB 后台登记的仓库（名称或 SVN 路径）完全一致；不确定就问管理员或在 RB 管理页查
- 卡住不动等输入 → 没配认证，rbt 在交互等密码；在 `.reviewboardrc` 配 `API_TOKEN`（推荐）或 `USERNAME`/`PASSWORD` 后重跑
- HTTP 401/403 → token 过期/被回收/只读 policy，或账号无权限访问该仓库；重新生成 token 或联系管理员
- 404 或返回登录页 HTML → `REVIEWBOARD_URL` 写错（不要带 /api 后缀），或被 SSO/反向代理拦截；浏览器能直接打开 RB 才说明地址对
- SSL 证书错误（内网自签名）→ 临时：`.reviewboardrc` 加 `DISABLE_SSL_VERIFICATION = True`；推荐：rbt 加 `--ca-certs` 指定公司 CA 证书
- 代理问题 → rbt 走系统代理，必要时加 `--disable-proxy`；本 skill 的 API 脚本走 `HTTPS_PROXY`/`HTTP_PROXY` 环境变量
- 新文件不在 diff 里 → 没 `svn add`（`svn status` 显示 `?`）；二进制文件同样要先 add
- 只想提部分文件 / changelist → 用 `rb_post.py -I 文件`，文件列表可来自 `svn status --cl 名字`
- 提审成功但 diff 为空 → 本地无改动，或改动全在未 add 的新文件里
- 更新后网页看不到新 diff → diff 有版本（revision）概念，页面右上角切到最新 revision

## rb_comments / rb_reply（REST API 脚本）

- 403 → 检查 `API_TOKEN` 是否有效、token policy 是否设了只读；回复/发布需要写权限
- 报"没找到评论" → 评论 ID 是 RB 全局 ID，不是 `rb_comments.py` 输出里的显示序号；用 `--json` 输出核对 `comment_id`
- 回复成功但网页看不到 → 回复必须发布后可见；脚本已自动 `public=true`，若 token policy 限制会直接报错
- 控制台中文乱码（Windows）→ `chcp 65001`，或加 `--json` 把输出重定向到文件查看

## 环境

- `svn` 不可用 → 装 TortoiseSVN（勾选 command line tools）或 SlikSVN
- `rbt` 不可用 → `pip install rbtools`
- Python 缺失 → 装 3.7+；本 skill 脚本只用标准库
