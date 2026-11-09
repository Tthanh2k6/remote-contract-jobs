"""Rate-limited GET transport with an expendable, atomic disk cache."""
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import time
from urllib.parse import urlsplit

import requests

from . import __version__

USER_AGENT = f"remote-contract-jobs/{__version__} (+https://github.com/Tthanh2k6/remote-contract-jobs)"
_LOCK = threading.Lock()
_LAST_REQUEST = {}


class Fetcher:
    def __init__(self, cache_dir=None, no_cache=False, ttl=1800, session=None):
        self.cache_dir = Path(cache_dir or Path.home() / ".cache" / "remote-contract-jobs")
        self.no_cache = no_cache
        self.ttl = ttl
        self.session = session or requests.Session()

    def get(self, url):
        path = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".cache")
        if not self.no_cache:
            try:
                if time.time() - path.stat().st_mtime < self.ttl:
                    return path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                pass
        host = urlsplit(url).netloc.lower()
        with _LOCK:
            delay = 1 - (time.monotonic() - _LAST_REQUEST.get(host, float("-inf")))
            if delay > 0:
                time.sleep(delay)
            _LAST_REQUEST[host] = time.monotonic()
            # No automatic redirects: every outgoing request must be rate limited.
            response = self.session.get(url, headers={"User-Agent": USER_AGENT}, timeout=20, allow_redirects=False)
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise ValueError(f"Unexpected redirect from {host}")
        response.encoding = "utf-8"
        text = response.text
        if not self.no_cache:
            temporary = None
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.cache_dir, delete=False) as stream:
                    temporary = stream.name
                    stream.write(text)
                os.replace(temporary, path)
            except OSError:
                pass  # Cache failure must not turn a successful fetch into an error.
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
        return text
