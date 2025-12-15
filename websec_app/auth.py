from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .db import fetch_many, fetch_one, get_db, log_action
from .security import hash_password, set_session_logged_in, verify_password

bp = Blueprint("auth", __name__)


def get_current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return fetch_one(
        "SELECT id, username, is_admin, display_name, description FROM users WHERE id = ?",
        (user_id,),
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(g, "user", None):
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(g, "user", None):
            return redirect(url_for("auth.login", next=request.full_path))
        if not bool(g.user.get("is_admin")):
            flash("需要管理员权限", "warning")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


@bp.get("/register")
def register():
    return render_template("register.html")


@bp.post("/register")
def register_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        flash("用户名和密码不能为空", "danger")
        return redirect(url_for("auth.register"))

    if fetch_one("SELECT id FROM users WHERE username = ?", (username,)):
        flash("用户名已存在", "warning")
        return redirect(url_for("auth.register"))

    count_row = fetch_one("SELECT COUNT(1) AS c FROM users")
    is_admin = 1 if int((count_row or {}).get("c", 0)) == 0 else 0

    get_db().execute(
        """
        INSERT INTO users (username, password_hash, is_admin, display_name, description, created_at, updated_at)
        VALUES (?, ?, ?, '', '', datetime('now'), datetime('now'))
        """,
        (username, hash_password(password), is_admin),
    )
    get_db().commit()
    user = fetch_one("SELECT id FROM users WHERE username = ?", (username,))
    log_action(user["id"], "register", f"username={username}")
    flash("注册成功，请登录", "success")
    return redirect(url_for("auth.login"))


@bp.get("/login")
def login():
    return render_template("login.html", next=request.args.get("next", ""))


@bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    next_url = request.form.get("next") or ""

    user_row = fetch_one("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    if not user_row or not verify_password(user_row["password_hash"], password):
        log_action(None, "login_failed", f"username={username}")
        flash("用户名或密码错误", "danger")
        return redirect(url_for("auth.login"))

    set_session_logged_in(int(user_row["id"]))
    log_action(int(user_row["id"]), "login", f"username={username}")
    flash("登录成功", "success")

    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("index"))


@bp.post("/logout")
@login_required
def logout():
    user_id = g.user["id"]
    session.clear()
    log_action(user_id, "logout", "")
    flash("已登出", "info")
    return redirect(url_for("index"))


@bp.get("/profile")
@login_required
def profile():
    return render_template("profile.html")


@bp.post("/profile")
@login_required
def profile_post():
    display_name = (request.form.get("display_name") or "").strip()
    description = (request.form.get("description") or "").strip()

    get_db().execute(
        "UPDATE users SET display_name = ?, description = ?, updated_at = datetime('now') WHERE id = ?",
        (display_name, description, g.user["id"]),
    )
    get_db().commit()
    log_action(g.user["id"], "profile_update", "")
    flash("已保存", "success")
    return redirect(url_for("auth.profile"))


@bp.post("/account/delete")
@login_required
def account_delete():
    confirm = (request.form.get("confirm") or "").strip()
    if confirm != g.user["username"]:
        flash("请输入你的用户名以确认删除", "warning")
        return redirect(url_for("auth.profile"))

    uid = g.user["id"]
    session.clear()
    get_db().execute("DELETE FROM users WHERE id = ?", (uid,))
    get_db().commit()
    log_action(None, "account_deleted", f"user_id={uid}")
    flash("账号已删除", "info")
    return redirect(url_for("index"))


@bp.get("/users")
@admin_required
def users():
    rows = fetch_many("SELECT id, username, is_admin, display_name, created_at FROM users ORDER BY id DESC")
    return render_template("users.html", users=rows)


@bp.post("/users/<int:user_id>/delete")
@admin_required
def user_delete(user_id: int):
    if int(user_id) == int(g.user["id"]):
        flash("不能在此处删除当前登录账号（请在个人资料中删除）", "warning")
        return redirect(url_for("auth.users"))

    target = fetch_one("SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,))
    if not target:
        flash("用户不存在", "warning")
        return redirect(url_for("auth.users"))

    get_db().execute("DELETE FROM users WHERE id = ?", (user_id,))
    get_db().commit()
    log_action(g.user["id"], "user_delete", f"target_id={user_id} username={target['username']}")
    flash("已删除用户", "info")
    return redirect(url_for("auth.users"))


@bp.get("/audit")
@login_required
def audit():
    rows = fetch_many(
        "SELECT id, action, detail, ip, ua, created_at FROM audit_logs WHERE user_id = ? ORDER BY id DESC LIMIT 200",
        (g.user["id"],),
    )
    return render_template("audit.html", logs=rows)


@bp.get("/api/audit")
@login_required
def api_audit():
    rows = fetch_many(
        "SELECT id, action, detail, ip, ua, created_at FROM audit_logs WHERE user_id = ? ORDER BY id DESC LIMIT 50",
        (g.user["id"],),
    )
    return {"logs": rows}
