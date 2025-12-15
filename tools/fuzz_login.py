from __future__ import annotations

import random
import string
import time
import urllib.parse

import requests


def _rand(n: int) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


def main() -> int:
    base = "http://127.0.0.1:5000"
    total = 50

    s = requests.Session()
    login_page = s.get(urllib.parse.urljoin(base, "/login"), timeout=5)
    if login_page.status_code != 200:
        print("cannot reach /login:", login_page.status_code)
        return 2

    # naive parse for csrf_token
    marker = 'name="csrf_token" value="'
    idx = login_page.text.find(marker)
    if idx < 0:
        print("csrf token not found")
        return 2
    start = idx + len(marker)
    end = login_page.text.find('"', start)
    csrf = login_page.text[start:end]

    t0 = time.time()
    for i in range(total):
        u = "nope_" + _rand(8)
        p = _rand(12)
        r = s.post(
            urllib.parse.urljoin(base, "/login"),
            data={"username": u, "password": p, "csrf_token": csrf, "next": ""},
            allow_redirects=False,
            timeout=5,
        )
        print(i, r.status_code, "len=", len(r.text))
    dt = time.time() - t0
    print("done", total, "requests in", f"{dt:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

