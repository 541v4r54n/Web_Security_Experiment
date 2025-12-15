from __future__ import annotations

import hmac
import ipaddress
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from flask import abort, current_app, request, session
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def require_csrf() -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    # Allow API clients to send CSRF token via header
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    token = session.get("_csrf_token")
    if not token or not sent or not hmac.compare_digest(token, sent):
        abort(400, description="Bad CSRF token")


def set_session_logged_in(user_id: int) -> None:
    session.clear()
    session["user_id"] = int(user_id)
    session["login_at"] = datetime.now(timezone.utc).isoformat()
    session.permanent = True

    minutes = int(current_app.config.get("SESSION_MINUTES", 60))
    current_app.permanent_session_lifetime = timedelta(minutes=minutes)


def validate_hostname_or_ip(value: str) -> bool:
    value = value.strip()
    if not value or len(value) > 253:
        return False

    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        pass

    if value.startswith("-") or value.endswith("-"):
        return False
    if ".." in value:
        return False
    if not re.fullmatch(r"[A-Za-z0-9.-]+", value):
        return False
    return True


def generate_self_signed_cert(cert_path: Path, key_path: Path, force: bool) -> None:
    if cert_path.exists() and key_path.exists() and not force:
        return

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WebSec Lab"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(private_key=key, algorithm=hashes.SHA256())
    )

    cert_path.parent.mkdir(parents=True, exist_ok=True)

    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

