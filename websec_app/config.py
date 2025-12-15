from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    secret_key: str
    var_dir: Path
    db_path: Path
    upload_dir: Path
    watermarked_dir: Path
    cert_dir: Path
    cert_crt_path: Path
    cert_key_path: Path
    session_minutes: int

    @staticmethod
    def load() -> "AppConfig":
        root = _root_dir()
        var_dir = root / "var"
        db_path = var_dir / "app.db"
        upload_dir = var_dir / "uploads"
        watermarked_dir = var_dir / "watermarked"
        cert_dir = var_dir / "certs"
        cert_crt_path = cert_dir / "localhost.crt"
        cert_key_path = cert_dir / "localhost.key"

        secret_key = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me")
        session_minutes = int(os.getenv("SESSION_MINUTES", "60"))

        return AppConfig(
            secret_key=secret_key,
            var_dir=var_dir,
            db_path=db_path,
            upload_dir=upload_dir,
            watermarked_dir=watermarked_dir,
            cert_dir=cert_dir,
            cert_crt_path=cert_crt_path,
            cert_key_path=cert_key_path,
            session_minutes=session_minutes,
        )

    def ensure_dirs(self) -> None:
        self.var_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.watermarked_dir.mkdir(parents=True, exist_ok=True)
        self.cert_dir.mkdir(parents=True, exist_ok=True)

    def as_flask_config(self) -> dict:
        return {
            "SECRET_KEY": self.secret_key,
            "DB_PATH": str(self.db_path),
            "UPLOAD_DIR": str(self.upload_dir),
            "WATERMARKED_DIR": str(self.watermarked_dir),
            "SESSION_MINUTES": self.session_minutes,
        }

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

