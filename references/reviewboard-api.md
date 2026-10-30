# ReviewBoard Web API 速查（rb_comments / rb_reply 使用）

## 认证（rb_common.build_auth_header）

- API token（推荐）：请求头 `Authorization: token <API_TOKEN>`，token 在 RB 网页 My Account -> API Tokens 生成
- 用户名密码：请求头 `Authorization: Basic base64(username:password)`
- 两者都不配时脚本直接报错

## 通用约定

- 基础地址：`REVIEWBOARD_URL`（不带 /api 后缀），接口前缀 `{base}/api/`
- 列表响应：`{"stat": "ok", "<资源名复数>": [...], "total_results": N, "links": {...}}`
- 资源对象内 `links.<name>.href` 是相关资源 URL，优先使用，不要手工拼路径
- 翻页：顶层 `links.next.href`，每页 `max-results=200`
- 常见失败：403（token 无效/只读 policy/未登录）、400（字段错误，看响应里的 err.msg）

## 用到的端点

| 用途 | 方法与路径 |
| --- | --- |
| 评审单详情 | GET /api/review-requests/{id}/ |
| 评审列表（回复也是 review 资源，带 reply_to 链接） | GET /api/review-requests/{id}/reviews/ |
| 某 review 的 diff 评论 | GET {review}.links.diff_comments.href（可加 &expand=filediff,interfilediff 内嵌文件名） |
| 某 review 的 general 评论 | GET {review}.links.general_comments.href |
| 对评审单发顶层评论 | POST /api/review-requests/{id}/reviews/，body: body_top；再 PUT {review}.links.self，body: public=true 发布 |
| 创建回复 draft | POST /api/review-requests/{id}/reviews/{rid}/replies/ |
| 回复具体评论 | POST {reply}.links.diff_comments.href 或 general_comments，body: reply_to_id, text |
| 标记 issue 状态 | PUT {reply_comment}.links.self，body: issue_status=resolved 或 dropped（仅原评论开了 issue） |
| 发布回复 | PUT {reply}.links.self，body: public=true |

## 关键字段

- review：`id`、`body_top`、`body_bottom`、`ship_it`、`timestamp`、`links.user.title`（用户名）、`links.reply_to`（存在则是回复）
- comment：`id`、`text`、`issue_open`、`issue_status`（open/resolved/dropped）、`first_line`、`num_lines`、`filediff.dest_file/source_file`、`links.reply_to.title`（原评论 ID）

## 相关 CLI（rbt）

- 关闭评审单：`rbt close <ID>`（默认 completed，旧服务端叫 submitted）；作废 `rbt close <ID> --close-type discarded`
- 我的在审列表：`rbt status`
- 评审单详情：`rbt info <ID>`
