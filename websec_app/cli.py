from __future__ import annotations

import argparse
import sys

from waitress import serve

from . import create_app
from .config import AppConfig
from .db import init_db
from .security import generate_self_signed_cert


def _cmd_init_db(_args: argparse.Namespace) -> int:
    cfg = AppConfig.load()
    cfg.ensure_dirs()
    init_db(cfg.db_path)
    return 0


def _cmd_gen_cert(args: argparse.Namespace) -> int:
    cfg = AppConfig.load()
    cfg.ensure_dirs()
    generate_self_signed_cert(
        cert_path=cfg.cert_crt_path,
        key_path=cfg.cert_key_path,
        force=bool(args.force),
    )
    return 0


def _cmd_self_check(_args: argparse.Namespace) -> int:
    cfg = AppConfig.load()
    cfg.ensure_dirs()
    init_db(cfg.db_path)
    generate_self_signed_cert(cert_path=cfg.cert_crt_path, key_path=cfg.cert_key_path, force=False)
    print("OK")
    print("db:", cfg.db_path)
    print("uploads:", cfg.upload_dir)
    print("watermarked:", cfg.watermarked_dir)
    print("cert:", cfg.cert_crt_path)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = AppConfig.load()
    cfg.ensure_dirs()

    app = create_app()
    host = args.host
    port = int(args.port)

    if args.https:
        generate_self_signed_cert(cert_path=cfg.cert_crt_path, key_path=cfg.cert_key_path, force=False)
        app.run(
            host=host,
            port=port,
            debug=False,
            ssl_context=(str(cfg.cert_crt_path), str(cfg.cert_key_path)),
        )
        return 0

    serve(app, host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="websec_app", description="Web安全实验平台（作业一&二）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="初始化/重建 sqlite 数据库")
    p_init.set_defaults(func=_cmd_init_db)

    p_cert = sub.add_parser("gen-cert", help="生成自签名 HTTPS 证书（localhost）")
    p_cert.add_argument("--force", action="store_true", help="覆盖已有证书")
    p_cert.set_defaults(func=_cmd_gen_cert)

    p_check = sub.add_parser("self-check", help="本地自检（目录/数据库/证书）")
    p_check.set_defaults(func=_cmd_self_check)

    p_run = sub.add_parser("run", help="启动服务")
    p_run.add_argument("--host", default="127.0.0.1")
    p_run.add_argument("--port", default="5000")
    p_run.add_argument("--https", action="store_true", help="启用 HTTPS（自签名证书）")
    p_run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return int(args.func(args))

