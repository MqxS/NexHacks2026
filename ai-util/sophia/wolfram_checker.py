from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request


class WolframAlphaChecker:
    def __init__(
        self,
        app_id: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.app_id = app_id or os.environ.get("WOLFRAM_APP_ID") or os.environ.get("WOLFRAM_APPID")
        if not self.app_id:
            raise RuntimeError("Missing WOLFRAM_APP_ID (or WOLFRAM_APPID).")
        self.timeout_s = timeout_s

    def result_text(self, query: str) -> str | None:
        q = query.strip()
        if not q:
            return None
        url = (
            "https://api.wolframalpha.com/v1/result?"
            + urllib.parse.urlencode({"i": q, "appid": self.app_id}, quote_via=urllib.parse.quote)
        )
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.read().decode("utf-8").strip()
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8")
            except Exception:
                body = None
            if e.code in (400, 501):
                return None if not body else body.strip()
            raise

    def has_answer(self, query: str) -> bool:
        res = self.result_text(query)
        if not res:
            return False
        if "Wolfram|Alpha did not understand" in res:
            return False
        return True

    def best_effort_answer(self, query: str) -> tuple[bool, str | None]:
        res = self.result_text(query)
        if not res:
            return False, None
        if "Wolfram|Alpha did not understand" in res:
            return False, res
        return True, res

