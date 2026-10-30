#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取 ReviewBoard 评审单上的评审意见。

用法：
  python rb_comments.py -r 1234          # 全部意见（文本）
  python rb_comments.py -r 1234 --open   # 只看 open issue
  python rb_comments.py -r 1234 --json   # 结构化 JSON
  python rb_comments.py -r 1234 --server https://rb.example.com  # 临时覆盖服务器
"""
import argparse
import json
import sys

from rb_common import (RBError, api, api_url, build_auth_header, link_href,
                       load_auth_config, paginate, resource_item, rr_url)


def comment_file(c):
    fd = c.get("filediff")
    if isinstance(fd, dict):
        name = fd.get("dest_file") or fd.get("source_file")
        if name:
            return name
    ifd = c.get("interfilediff")
    if isinstance(ifd, dict):
        name = ifd.get("dest_file") or ifd.get("source_file")
        if name:
            return name
    return None


def collect(base, auth, rr_id):
    rr = resource_item(api("GET", rr_url(base, rr_id), auth))
    reviews = paginate(f"{rr_url(base, rr_id)}reviews/", auth)
    data = {
        "review_request": {
            "id": rr.get("id"),
            "summary": rr.get("summary"),
            "status": rr.get("status"),
        },
        "reviews": [],
    }
    for review in reviews:
        entry = {
            "review_id": review.get("id"),
            "author": (review.get("links", {}).get("user", {}) or {}).get("title") or "?",
            "timestamp": review.get("timestamp"),
            "ship_it": bool(review.get("ship_it")),
            "reply_to_review": (review.get("links", {}).get("reply_to", {}) or {}).get("title"),
            "body_top": review.get("body_top") or "",
            "comments": [],
        }
        for kind in ("diff_comments", "general_comments"):
            href = link_href(review, kind)
            if not href:
                continue
            try:
                items = paginate(href, auth, params={"expand": "filediff,interfilediff"})
            except RBError:
                items = paginate(href, auth)
            for c in items:
                entry["comments"].append({
                    "comment_id": c.get("id"),
                    "kind": "diff" if kind == "diff_comments" else "general",
                    "file": comment_file(c),
                    "first_line": c.get("first_line"),
                    "num_lines": c.get("num_lines"),
                    "issue_open": bool(c.get("issue_open")),
                    "issue_status": c.get("issue_status"),
                    "reply_to": (c.get("links", {}).get("reply_to", {}) or {}).get("title"),
                    "text": c.get("text") or "",
                })
        data["reviews"].append(entry)
    return data


def render(data, only_open):
    rr = data["review_request"]
    lines = [f"=== Review Request #{rr['id']}: {rr.get('summary') or '(无标题)'} "
             f"[status={rr.get('status')}] ==="]
    seq = 0
    shown = 0
    for rev in data["reviews"]:
        head = (f"[review {rev['review_id']}] {rev['author']} @ {rev['timestamp']}"
                f" · ship_it={'是' if rev['ship_it'] else '否'}")
        if rev["reply_to_review"]:
            head += f" · 回复 review {rev['reply_to_review']}"
        lines.append(head)
        if rev["body_top"].strip():
            lines.append(f"  整体意见: {rev['body_top'].strip()}")
        for c in rev["comments"]:
            seq += 1
            is_open = c["issue_open"] and c["issue_status"] != "resolved"
            if only_open and not is_open:
                continue
            shown += 1
            if c["file"]:
                loc = f" {c['file']} L{c['first_line']}"
                if (c.get("num_lines") or 1) > 1:
                    loc += f"+{c['num_lines']}"
            else:
                loc = ""
            issue = f"issue:{c['issue_status'] or ('open' if c['issue_open'] else '无')}"
            tag = f" · 回复 #{c['reply_to']}" if c["reply_to"] else ""
            lines.append(f"  #{seq} [comment {c['comment_id']}] {c['kind']}{loc} · {issue}{tag}")
            for t in (c["text"] or "").strip().splitlines():
                lines.append(f"      {t}")
    lines.append(f"\n共 {shown if only_open else seq} 条评论" + ("（open issue）" if only_open else ""))
    rid = data["review_request"]["id"]
    lines.append("回复示例:")
    lines.append(f'  python rb_reply.py -r {rid} --comment <comment_id> --message "..." --resolve')
    lines.append(f'  python rb_reply.py -r {rid} --review <review_id> --message "..."')
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="查看 ReviewBoard 评审单上的评审意见")
    ap.add_argument("-r", "--review-id", required=True, help="评审单 ID")
    ap.add_argument("--open", action="store_true", help="只看 open issue")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--server", help="覆盖 .reviewboardrc 里的 REVIEWBOARD_URL")
    args = ap.parse_args()

    cfg, _ = load_auth_config()
    if args.server:
        cfg["REVIEWBOARD_URL"] = args.server
    base = api_url(cfg)
    auth = build_auth_header(cfg)
    data = collect(base, auth, args.review_id)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render(data, args.open))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RBError as e:
        print(f"[错误] {e}")
        sys.exit(1)
