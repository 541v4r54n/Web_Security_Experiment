from __future__ import annotations

import os
import subprocess

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import fetch_many, get_db, log_action
from .security import validate_hostname_or_ip

bp = Blueprint("labs", __name__, url_prefix="/labs")


@bp.get("")
@login_required
def index():
    return render_template("labs/index.html")


@bp.get("/sql-injection")
@login_required
def sql_injection_page():
    return render_template("labs/sql_injection.html", insecure=None, secure=None)


@bp.post("/sql-injection/insecure")
@login_required
def sql_injection_insecure():
    keyword = (request.form.get("keyword") or "").strip()

    # 漏洞演示：把用户输入拼接进 SQL 字符串（仅用于实验演示）
    sql = (
        "SELECT id, title, content FROM notes "
        f"WHERE title LIKE '%{keyword}%' OR content LIKE '%{keyword}%' "
        "ORDER BY id DESC LIMIT 50"
    )

    try:
        cur = get_db().execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        err = None
    except Exception as e:
        rows = []
        err = str(e)

    log_action(g.user["id"], "lab_sql_injection_insecure", keyword)
    return render_template(
        "labs/sql_injection.html",
        insecure={"keyword": keyword, "sql": sql, "rows": rows, "error": err},
        secure=None,
    )


@bp.post("/sql-injection/secure")
@login_required
def sql_injection_secure():
    keyword = (request.form.get("keyword") or "").strip()
    like = f"%{keyword}%"

    sql = (
        "SELECT id, title, content FROM notes "
        "WHERE title LIKE ? OR content LIKE ? "
        "ORDER BY id DESC LIMIT 50"
    )

    rows = fetch_many(sql, (like, like))
    log_action(g.user["id"], "lab_sql_injection_secure", keyword)
    return render_template(
        "labs/sql_injection.html",
        insecure=None,
        secure={"keyword": keyword, "sql": sql, "rows": rows, "error": None},
    )


@bp.get("/command-injection")
@login_required
def command_injection_page():
    return render_template("labs/command_injection.html", insecure=None, secure=None)


def _ping_cmd(host: str) -> list[str]:
    count_flag = "-n" if os.name == "nt" else "-c"
    return ["ping", count_flag, "1", host]


@bp.post("/command-injection/insecure")
@login_required
def command_injection_insecure():
    host = (request.form.get("host") or "").strip()
    if not host:
        flash("请输入 host", "warning")
        return redirect(url_for("labs.command_injection_page"))

    # 漏洞演示：shell=True + 拼接用户输入（仅用于实验演示）
    cmd = " ".join(_ping_cmd(host))
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=4)
        out = (p.stdout + "\n" + p.stderr).strip()
        out = out[:4000]
        err = None
    except Exception as e:
        out = ""
        err = str(e)

    log_action(g.user["id"], "lab_command_injection_insecure", host)
    return render_template(
        "labs/command_injection.html",
        insecure={"host": host, "cmd": cmd, "output": out, "error": err},
        secure=None,
    )


@bp.post("/command-injection/secure")
@login_required
def command_injection_secure():
    host = (request.form.get("host") or "").strip()
    if not validate_hostname_or_ip(host):
        flash("host 格式不合法（仅允许域名或 IP）", "danger")
        return redirect(url_for("labs.command_injection_page"))

    cmd = _ping_cmd(host)
    try:
        p = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=4)
        out = (p.stdout + "\n" + p.stderr).strip()
        out = out[:4000]
        err = None
    except Exception as e:
        out = ""
        err = str(e)

    log_action(g.user["id"], "lab_command_injection_secure", host)
    return render_template(
        "labs/command_injection.html",
        insecure=None,
        secure={"host": host, "cmd": " ".join(cmd), "output": out, "error": err},
    )

