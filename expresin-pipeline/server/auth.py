"""ExpResin 认证与授权（auth_v1）。

设计要点：
- 密码哈希：hashlib.pbkdf2_hmac（Python 标准库，无新依赖），
  存储格式 ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``。
- 会话令牌：不透明 Bearer token（secrets.token_urlsafe），落 auth_tokens 表，
  支持吊销与过期（默认 7 天），改密后可踢掉其他会话。
- FastAPI 依赖：``get_current_user`` / ``require_admin``，从
  ``Authorization: Bearer <token>`` 解析用户；store 单例经 ``app.state.store`` 注入，
  避免与本模块循环导入。
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, Request

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 200_000
TOKEN_TTL_DAYS = 7

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")
MIN_PASSWORD_LEN = 6


# --------------------------------------------------------------------------- #
# 密码
# --------------------------------------------------------------------------- #


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS
    ).hex()
    return f"{ALGORITHM}${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$", 3)
        if algo != ALGORITHM:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, AttributeError):
        return False


def validate_username(username: str) -> str | None:
    """返回错误信息；合法返回 None。用户名限 ASCII 便于口头传达与登录输入。"""
    if not USERNAME_RE.match(username or ""):
        return "用户名需为 3-32 位字母、数字或 _ . -"
    return None


def validate_password(password: str) -> str | None:
    if len(password or "") < MIN_PASSWORD_LEN:
        return f"密码至少 {MIN_PASSWORD_LEN} 位"
    return None


def public_user(user: dict) -> dict:
    """剥离敏感字段后的用户视图。"""
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user.get("display_name") or user["username"],
        "role": user.get("role", "user"),
        "must_change_password": bool(user.get("must_change_password")),
        "created_at": user.get("created_at"),
    }


def new_user_id() -> str:
    return f"usr_{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- #
# 令牌
# --------------------------------------------------------------------------- #


def issue_token(store, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=TOKEN_TTL_DAYS)).isoformat(timespec="seconds")
    store.create_token(token, user_id, expires_at)
    return token


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip() or None
    return None


# --------------------------------------------------------------------------- #
# FastAPI 依赖
# --------------------------------------------------------------------------- #


def get_current_user(request: Request) -> dict:
    """解析当前登录用户；未登录/令牌失效返回 401（前端据此跳回登录页）。"""
    token = _bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user = request.app.state.store.get_token_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    # 把当前令牌挂在返回值上，logout / change-password 需要定位本会话
    user["_token"] = token
    return user


def require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
