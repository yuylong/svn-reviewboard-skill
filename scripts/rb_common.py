#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""svn-reviewboard 公共模块。

- .reviewboardrc 配置发现与解析（Python 语法，与 RBTools 官方约定一致）
- ReviewBoard REST API 调用（token 或密码认证，urllib 实现，无第三方依赖）
"""
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CONFIG_NAME = ".reviewboardrc"
KNOWN_KEYS = (
    "REVIEWBOARD_URL", "REPOSITORY", "REPOSITORY_URL", "API_TOKEN",
    "USERNAME", "PASSWORD", "TARGET_PEOPLE", "TARGET_GROUPS", "BRANCH",
    "DISABLE_SSL_VERIFICATION",
)


class RBError(Exception):
    """可读的业务/配置错误，直接展示给用户。"""


# DISABLE_SSL_VERIFICATION = True 时使用不校验证书的 SSL 上下文（内网自签名场景，
# 经用户确认启用）。风险：不再验证服务器身份。
_SSL_CONTEXT = None


def apply_ssl_config(cfg):
    global _SSL_CONTEXT
    if cfg.get("DISABLE_SSL_VERIFICATION"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _SSL_CONTEXT = ctx
    else:
        _SSL_CONTEXT = None


def mask(value):
    if not value:
        return "(未配置)"
    s = str(value)
    return s[:4] + "****" if len(s) > 8 else "****"


def find_config(start_dir=None):
    """从 start_dir（默认当前目录）逐级向上找 .reviewboardrc，找不到回退用户主目录。"""
    d = os.path.abspath(start_dir or os.getcwd())
    while True:
        p = os.path.join(d, CONFIG_NAME)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    home = os.path.join(os.path.expanduser("~"), CONFIG_NAME)
    return home if os.path.isfile(home) else None


def load_config(path):
    """解析 .reviewboardrc（Python 语法），只保留已知键。"""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    cfg = {}
    exec(compile(source, path, "exec"), cfg)
    return {k: v for k, v in cfg.items() if k in KNOWN_KEYS}


def load_auth_config(config_path=None):
    """加载配置，返回 (cfg, path)；没有配置或缺 REVIEWBOARD_URL 时报错。"""
    path = config_path or find_config()
    if not path:
        raise RBError(
            "未找到 .reviewboardrc。请把 skill 的 assets/reviewboardrc 复制到 SVN 仓库"
            "根目录并改名为 .reviewboardrc，填好 REVIEWBOARD_URL 与认证信息。"
        )
    cfg = load_config(path)
    if not cfg.get("REVIEWBOARD_URL"):
        raise RBError(f"{path} 里缺少 REVIEWBOARD_URL")
    apply_ssl_config(cfg)
    return cfg, path


def build_auth_header(cfg):
    """生成 Authorization 头：token 认证为 'token <token>'，密码认证为 Basic。"""
    token = cfg.get("API_TOKEN")
    if token:
        return "token " + str(token).strip()
    username, password = cfg.get("USERNAME"), cfg.get("PASSWORD")
    if username and password:
        raw = f"{username}:{password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")
    raise RBError(
        "缺少认证信息：推荐在 .reviewboardrc 里配置 API_TOKEN"
        "（RB 网页 My Account -> API Tokens 生成），或配置 USERNAME + PASSWORD"
    )


def api(method, url, auth_header, data=None, params=None, timeout=60):
    """调用 ReviewBoard REST API，返回解析后的 JSON dict；错误转成可读 RBError。"""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    body = None
    headers = {"Authorization": auth_header, "Accept": "application/json"}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        hint = ""
        if e.code in (401, 403):
            hint = "（认证失败：检查 API_TOKEN/用户名密码，token 是否过期或只读）"
        raise RBError(f"API {method} 失败 HTTP {e.code}{hint}\nURL: {url}\n响应: {detail[:800]}")
    except urllib.error.URLError as e:
        raise RBError(f"网络错误：{e.reason}\nURL: {url}（检查服务器地址、VPN/代理、https 证书）")
    if not raw:
        raise RBError(f"API 返回空响应：{url}")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise RBError(f"API 返回非 JSON（可能被网关/SSO 重定向到登录页）：{url}\n响应开头: {raw[:200]}")
    if payload.get("stat") != "ok":
        errs = payload.get("err", {})
        raise RBError(f"API 返回错误 {errs.get('code')}: {errs.get('msg')}\nURL: {url}")
    return payload


def list_items(payload):
    for key, value in payload.items():
        if isinstance(value, list):
            return value
    return []


def resource_item(payload):
    skip = {"stat", "uri", "total_results", "links"}
    for key, value in payload.items():
        if key in skip or not isinstance(value, dict):
            continue
        if "links" in value:
            return value
    for key, value in payload.items():
        if key not in skip and isinstance(value, dict):
            return value
    return {}


def link_href(obj, name):
    return obj.get("links", {}).get(name, {}).get("href")


def api_url(cfg):
    return str(cfg["REVIEWBOARD_URL"]).rstrip("/")


def rr_url(base, rr_id):
    return f"{base}/api/review-requests/{rr_id}/"


def paginate(url, auth_header, params=None):
    """翻页拉取列表资源，返回 items 列表。"""
    params = dict(params or {})
    params.setdefault("max-results", 200)
    items = []
    while url:
        payload = api("GET", url, auth_header, params=params)
        items.extend(list_items(payload))
        url = (payload.get("links", {}).get("next", {}) or {}).get("href")
        params = None  # next 的 href 已自带参数
    return items
