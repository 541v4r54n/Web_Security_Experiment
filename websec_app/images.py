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


@bp.get("/images")
@login_required
def index():
    return render_template("images.html")


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
        "SELECT id, original_name, watermarked_name, watermark_text, created_at FROM images WHERE id = ? AND user_id = ?",
        (image_id, g.user["id"]),
    )
    if not row:
        flash("图片不存在或无权限", "warning")
        return redirect(url_for("images.index"))
    return render_template("image_detail.html", image=row)


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


@bp.get("/api/images")
@login_required
def api_images():
    rows = fetch_many(
        "SELECT id, original_name, watermark_text, created_at FROM images WHERE user_id = ? ORDER BY id DESC LIMIT 200",
        (g.user["id"],),
    )
    return {"images": rows}

