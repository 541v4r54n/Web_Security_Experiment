from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, flash, g, redirect, render_template, request, send_file, url_for, current_app
from werkzeug.utils import secure_filename

from .auth import login_required
from .db import fetch_many, fetch_one, get_db, log_action
from .watermark import add_text_watermark

bp = Blueprint("images", __name__)


def _paths_for(stored_name: str, watermarked_name: str) -> tuple[Path, Path]:
    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    wm_dir = Path(current_app.config["WATERMARKED_DIR"])
    return upload_dir / stored_name, wm_dir / watermarked_name


def _get_int_arg(name: str, default: int, *, min_value: int, max_value: int) -> int:
    raw = (request.args.get(name) or "").strip()
    try:
        value = int(raw)
    except Exception:
        value = default
    return max(min_value, min(max_value, value))


def _safe_next_url(value: str) -> str | None:
    value = (value or "").strip()
    if value.startswith("/images"):
        return value
    return None


def _page_items(page: int, pages: int, *, window: int = 2) -> list[int | None]:
    if pages <= 1:
        return [1]

    items: list[int | None] = [1]
    start = max(2, page - window)
    end = min(pages - 1, page + window)
    if start > 2:
        items.append(None)
    items.extend(range(start, end + 1))
    if end < pages - 1:
        items.append(None)
    items.append(pages)
    return items


def _delete_files(stored_name: str, watermarked_name: str) -> None:
    src_path, dst_path = _paths_for(stored_name, watermarked_name)
    try:
        src_path.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        dst_path.unlink(missing_ok=True)
    except Exception:
        pass


@bp.get("/images")
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    per_page = _get_int_arg("per_page", 12, min_value=6, max_value=60)
    page = _get_int_arg("page", 1, min_value=1, max_value=10_000)

    where = "user_id = ?"
    params: list[object] = [g.user["id"]]
    if q:
        where += " AND (original_name LIKE ? OR watermark_text LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])

    total_row = fetch_one(f"SELECT COUNT(1) AS c FROM images WHERE {where}", tuple(params))
    total = int((total_row or {}).get("c", 0))
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    offset = (page - 1) * per_page

    images = fetch_many(
        f"""
        SELECT id, original_name, watermark_text, created_at
        FROM images
        WHERE {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [per_page, offset]),
    )

    return render_template(
        "images.html",
        images=images,
        q=q,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        page_items=_page_items(page, pages),
    )


@bp.post("/images/upload")
@login_required
def upload():
    file = request.files.get("image")
    watermark_text = (request.form.get("watermark_text") or "").strip()

    if not file or not file.filename:
        flash("请选择图片文件", "warning")
        return redirect(url_for("images.index"))

    original_name = secure_filename(file.filename)
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        flash("仅支持 png/jpg/jpeg/bmp/webp", "danger")
        return redirect(url_for("images.index"))

    stored_name = f"{uuid4().hex}{suffix}"
    watermarked_name = f"{uuid4().hex}.jpg"
    src_path, dst_path = _paths_for(stored_name, watermarked_name)

    src_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(str(src_path))

    try:
        add_text_watermark(src_path, dst_path, watermark_text)
    except Exception:
        # cleanup best-effort
        try:
            src_path.unlink(missing_ok=True)
        except Exception:
            pass
        flash("水印处理失败（请更换图片重试）", "danger")
        return redirect(url_for("images.index"))

    get_db().execute(
        """
        INSERT INTO images (user_id, original_name, stored_name, watermarked_name, watermark_text, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (g.user["id"], original_name, stored_name, watermarked_name, watermark_text),
    )
    get_db().commit()
    log_action(g.user["id"], "image_upload", original_name)
    flash("上传成功，已生成水印图", "success")
    return redirect(url_for("images.index"))


@bp.get("/images/<int:image_id>")
@login_required
def detail(image_id: int):
    row = fetch_one(
        "SELECT id, original_name, stored_name, watermarked_name, watermark_text, created_at FROM images WHERE id = ? AND user_id = ?",
        (image_id, g.user["id"]),
    )
    if not row:
        flash("图片不存在或无权限", "warning")
        return redirect(url_for("images.index"))
    return render_template("image_detail.html", image=row)


@bp.get("/images/<int:image_id>/preview")
@login_required
def preview(image_id: int):
    row = fetch_one(
        "SELECT watermarked_name FROM images WHERE id = ? AND user_id = ?",
        (image_id, g.user["id"]),
    )
    if not row:
        flash("图片不存在或无权限", "warning")
        return redirect(url_for("images.index"))

    wm_dir = Path(current_app.config["WATERMARKED_DIR"])
    path = wm_dir / row["watermarked_name"]
    if not path.exists():
        flash("文件缺失，请重新上传生成", "danger")
        return redirect(url_for("images.index"))

    return send_file(path, as_attachment=False)


@bp.get("/images/<int:image_id>/original")
@login_required
def original(image_id: int):
    row = fetch_one(
        "SELECT stored_name FROM images WHERE id = ? AND user_id = ?",
        (image_id, g.user["id"]),
    )
    if not row:
        flash("图片不存在或无权限", "warning")
        return redirect(url_for("images.index"))

    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    path = upload_dir / row["stored_name"]
    if not path.exists():
        flash("原图文件缺失", "danger")
        return redirect(url_for("images.index"))

    return send_file(path, as_attachment=False)


@bp.get("/images/<int:image_id>/download")
@login_required
def download(image_id: int):
    row = fetch_one(
        "SELECT watermarked_name, original_name FROM images WHERE id = ? AND user_id = ?",
        (image_id, g.user["id"]),
    )
    if not row:
        flash("图片不存在或无权限", "warning")
        return redirect(url_for("images.index"))

    wm_dir = Path(current_app.config["WATERMARKED_DIR"])
    path = wm_dir / row["watermarked_name"]
    if not path.exists():
        flash("文件缺失，请重新上传生成", "danger")
        return redirect(url_for("images.index"))

    download_name = f"watermarked-{Path(row['original_name']).stem}.jpg"
    return send_file(path, as_attachment=True, download_name=download_name)


@bp.post("/images/bulk")
@login_required
def bulk_action():
    action = (request.form.get("action") or "").strip()
    next_url = _safe_next_url(request.form.get("next") or "")

    raw_ids = request.form.getlist("image_ids")
    try:
        image_ids = sorted({int(x) for x in raw_ids if str(x).strip()})
    except Exception:
        image_ids = []

    if not image_ids:
        flash("请先勾选图片记录", "warning")
        return redirect(next_url or url_for("images.index"))

    placeholders = ",".join("?" for _ in image_ids)
    rows = fetch_many(
        f"""
        SELECT id, stored_name, watermarked_name, original_name, watermark_text
        FROM images
        WHERE user_id = ? AND id IN ({placeholders})
        """,
        tuple([g.user["id"]] + image_ids),
    )

    by_id = {int(r["id"]): r for r in rows}
    found_ids = sorted(by_id.keys())
    if not found_ids:
        flash("未找到可操作的记录", "warning")
        return redirect(next_url or url_for("images.index"))

    if action == "delete":
        for image_id in found_ids:
            r = by_id[image_id]
            _delete_files(r["stored_name"], r["watermarked_name"])

        placeholders2 = ",".join("?" for _ in found_ids)
        get_db().execute(
            f"DELETE FROM images WHERE user_id = ? AND id IN ({placeholders2})",
            tuple([g.user["id"]] + found_ids),
        )
        get_db().commit()
        log_action(g.user["id"], "image_bulk_delete", f"count={len(found_ids)}")
        flash(f"已删除 {len(found_ids)} 条记录", "info")
        return redirect(next_url or url_for("images.index"))

    if action == "regenerate":
        new_text = (request.form.get("watermark_text") or "").strip()
        ok = 0
        failed = 0

        for image_id in found_ids:
            r = by_id[image_id]
            text = new_text or (r.get("watermark_text") or "")
            src_path, _old_dst_path = _paths_for(r["stored_name"], r["watermarked_name"])
            if not src_path.exists():
                failed += 1
                continue

            new_watermarked_name = f"{uuid4().hex}.jpg"
            _src_path, new_dst_path = _paths_for(r["stored_name"], new_watermarked_name)
            try:
                add_text_watermark(src_path, new_dst_path, text)
            except Exception:
                try:
                    new_dst_path.unlink(missing_ok=True)
                except Exception:
                    pass
                failed += 1
                continue

            try:
                _old_dst_path.unlink(missing_ok=True)
            except Exception:
                pass

            get_db().execute(
                "UPDATE images SET watermarked_name = ?, watermark_text = ? WHERE id = ? AND user_id = ?",
                (new_watermarked_name, text, image_id, g.user["id"]),
            )
            ok += 1

        get_db().commit()
        log_action(g.user["id"], "image_bulk_regenerate", f"ok={ok} failed={failed}")
        if ok and failed:
            flash(f"已重新生成 {ok} 条，失败 {failed} 条（原图文件缺失或处理失败）", "warning")
        elif ok:
            flash(f"已重新生成 {ok} 条水印图", "success")
        else:
            flash("重新生成失败（原图文件缺失或处理失败）", "danger")
        return redirect(next_url or url_for("images.index"))

    flash("不支持的操作", "danger")
    return redirect(next_url or url_for("images.index"))


@bp.post("/images/<int:image_id>/delete")
@login_required
def delete(image_id: int):
    row = fetch_one(
        "SELECT id, stored_name, watermarked_name, original_name FROM images WHERE id = ? AND user_id = ?",
        (image_id, g.user["id"]),
    )
    if not row:
        flash("图片不存在或无权限", "warning")
        return redirect(url_for("images.index"))

    _delete_files(row["stored_name"], row["watermarked_name"])

    get_db().execute("DELETE FROM images WHERE id = ? AND user_id = ?", (image_id, g.user["id"]))
    get_db().commit()
    log_action(g.user["id"], "image_delete", row["original_name"])
    flash("已删除", "info")
    return redirect(url_for("images.index"))


@bp.get("/api/images")
@login_required
def api_images():
    q = (request.args.get("q") or "").strip()
    per_page = _get_int_arg("per_page", 200, min_value=1, max_value=200)
    page = _get_int_arg("page", 1, min_value=1, max_value=10_000)

    where = "user_id = ?"
    params: list[object] = [g.user["id"]]
    if q:
        where += " AND (original_name LIKE ? OR watermark_text LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])

    offset = (page - 1) * per_page
    rows = fetch_many(
        f"""
        SELECT id, original_name, watermark_text, created_at
        FROM images
        WHERE {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [per_page, offset]),
    )
    return {"images": rows, "page": page, "per_page": per_page}
