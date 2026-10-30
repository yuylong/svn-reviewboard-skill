#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回复 ReviewBoard 评审意见（脚本发布后立即生效）。

用法：
  # 回复某条评论，并可顺带把 issue 标记为 resolved / dropped
  python rb_reply.py -r 1234 --comment 881 --message "已在 r2 修复" --resolve
  # 对某条 review 顶层回复
  python rb_reply.py -r 1234 --review 55 --message "收到，已处理"
  # 对整个评审单发顶层评论
  python rb_reply.py -r 1234 --message "已按意见更新 diff"

说明：
- --resolve/--drop 仅在 --comment 且原评论开启了 issue 时有效
- 回复对象是评论 ID / review ID，先用 rb_comments.py 查
"""
import argparse
import sys

from rb_common import (RBError, api, api_url, build_auth_header, link_href,
                       load_auth_config, paginate, resource_item, rr_url)


def find_comment(base, auth, rr_id, comment_id):
    """在评审单所有 review 里定位评论，返回 (review_id, kind, comment)。"""
    reviews = paginate(f"{rr_url(base, rr_id)}reviews/", auth)
    for review in reviews:
        for kind in ("diff_comments", "general_comments"):
            href = link_href(review, kind)
            if not href:
                continue
            for c in paginate(href, auth):
                if str(c.get("id")) == str(comment_id):
                    return review.get("id"), kind, c
    raise RBError(f"在评审单 {rr_id} 上没找到评论 {comment_id}；先用 rb_comments.py -r {rr_id} 确认 ID")


def main():
    ap = argparse.ArgumentParser(description="回复 ReviewBoard 评审意见")
    ap.add_argument("-r", "--review-id", required=True, help="评审单 ID")
    ap.add_argument("--comment", help="要回复的评论 ID")
    ap.add_argument("--review", help="要回复的 review ID（某人的一次评审）")
    ap.add_argument("--message", required=True, help="回复内容")
    ap.add_argument("--resolve", action="store_true", help="顺带把原评论 issue 标记为已解决")
    ap.add_argument("--drop", action="store_true", help="顺带把原评论 issue 标记为放弃")
    ap.add_argument("--server", help="覆盖 .reviewboardrc 里的 REVIEWBOARD_URL")
    args = ap.parse_args()

    if args.comment and args.review:
        print("[错误] --comment 和 --review 只能选一个")
        return 2
    if (args.resolve or args.drop) and not args.comment:
        print("[错误] --resolve/--drop 只能配合 --comment 使用")
        return 2
    if args.resolve and args.drop:
        print("[错误] --resolve 和 --drop 不能同时用")
        return 2

    cfg, _ = load_auth_config()
    if args.server:
        cfg["REVIEWBOARD_URL"] = args.server
    base = api_url(cfg)
    auth = build_auth_header(cfg)
    rr_base = rr_url(base, args.review_id)

    if args.comment:
        parent_review_id, kind, original = find_comment(base, auth, args.review_id, args.comment)
    elif args.review:
        parent_review_id, kind, original = args.review, None, None
    else:
        parent_review_id, kind, original = None, None, None

    if parent_review_id is not None:
        # 创建回复 draft（回复本身是一个 review 资源）
        reply = resource_item(api(
            "POST", f"{rr_base}reviews/{parent_review_id}/replies/", auth))
        reply_url = link_href(reply, "self")
        if kind:
            # 对具体评论的回复
            created = resource_item(api("POST", link_href(reply, kind), auth, data={
                "reply_to_id": args.comment,
                "text": args.message,
            }))
            if args.resolve or args.drop:
                if not original.get("issue_open"):
                    print("[提示] 原评论没有开启 issue，跳过 issue 状态标记")
                else:
                    api("PUT", link_href(created, "self"), auth, data={
                        "issue_status": "resolved" if args.resolve else "dropped"})
        else:
            # 对整条 review 的顶层回复
            api("PUT", reply_url, auth, data={"body_top": args.message})
        api("PUT", reply_url, auth, data={"public": "true"})
        print(f"[完成] 已发布{'评论回复' if kind else '顶层回复'}（review {parent_review_id}）")
    else:
        # 对评审单本身发一条新评论（新建 review draft 并发布）
        review = resource_item(api("POST", f"{rr_base}reviews/", auth, data={
            "body_top": args.message}))
        api("PUT", link_href(review, "self"), auth, data={"public": "true"})
        print("[完成] 已在评审单上发布顶层评论")

    print(f"[完成] 评审单页面: {base}/r/{args.review_id}/")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RBError as e:
        print(f"[错误] {e}")
        sys.exit(1)
