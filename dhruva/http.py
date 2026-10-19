"""Polite HTTP client: one shared cookie jar, retries with backoff, rate limit."""
from __future__ import annotations

import http.cookiejar
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 DhruvaTerminal/0.1"
)
MIN_INTERVAL_S = 0.4

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last_request = 0.0


class FetchError(RuntimeError):
    pass


def _throttle() -> None:
    global _last_request
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def get_bytes(url: str, params: dict | None = None, headers: dict | None = None,
              retries: int = 4, timeout: float = 60.0) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    hdrs.update(headers or {})
    delay = 2.0
    for attempt in range(retries + 1):
        _throttle()
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with _opener.open(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            # 4xx other than 429 will not get better on retry.
            if exc.code != 429 and 400 <= exc.code < 500:
                raise FetchError(f"HTTP {exc.code} for {url}") from exc
            err: Exception = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            err = exc
        if attempt < retries:
            log.warning("retry %d for %s (%s)", attempt + 1, url, err)
            time.sleep(delay)
            delay *= 2
    raise FetchError(f"giving up on {url}: {err}")


def get_text(url: str, params: dict | None = None, **kw) -> str:
    return get_bytes(url, params, **kw).decode("utf-8", errors="replace")


def get_json(url: str, params: dict | None = None, **kw):
    hdrs = {"Accept": "application/json"}
    hdrs.update(kw.pop("headers", {}) or {})
    return json.loads(get_bytes(url, params, headers=hdrs, **kw))


def warm(url: str) -> None:
    """Visit a page to collect session cookies; failures are fine."""
    try:
        get_bytes(url, retries=0, timeout=20)
    except FetchError:
        pass
