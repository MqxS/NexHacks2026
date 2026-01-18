from __future__ import annotations

import json
import os
import pathlib
import typing as t


REQUIRED_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "WOLFRAM_APP_ID",
    "WOLFRAM_APPID",
    "TOKENC_API_KEY",
)


def _parse_dotenv(content: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            continue
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]
        out[key] = val
    return out


def _load_dotenv_file(path: pathlib.Path) -> dict[str, str]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return _parse_dotenv(content)


def _resolve_repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    return here.parent.parent


def _coalesce_env(primary: str, aliases: list[str]) -> str | None:
    v = os.environ.get(primary)
    if v:
        return v
    for a in aliases:
        v2 = os.environ.get(a)
        if v2:
            return v2
    return None


def initialize_env_vars(
    *,
    gemini_api_key: str | None = None,
    wolfram_app_id: str | None = None,
    tokenc_api_key: str | None = None,
    dotenv_paths: list[str] | None = None,
    override_existing: bool = False,
) -> dict[str, bool]:
    repo_root = _resolve_repo_root()
    candidates = [
        repo_root / ".env",
        repo_root / ".env.local",
        repo_root / "ai-util" / ".env",
        repo_root / "ai-util" / ".env.local",
    ]
    if dotenv_paths:
        candidates = [pathlib.Path(p).expanduser().resolve() for p in dotenv_paths] + candidates

    loaded: dict[str, str] = {}
    for p in candidates:
        loaded.update(_load_dotenv_file(p))

    def set_env(k: str, v: str | None) -> None:
        if v is None or v == "":
            return
        if not override_existing and os.environ.get(k):
            return
        os.environ[k] = v

    if gemini_api_key:
        set_env("GEMINI_API_KEY", gemini_api_key)
    if wolfram_app_id:
        set_env("WOLFRAM_APP_ID", wolfram_app_id)
    if tokenc_api_key:
        set_env("TOKENC_API_KEY", tokenc_api_key)

    for k, v in loaded.items():
        if k in REQUIRED_KEYS:
            set_env(k, v)

    g = _coalesce_env("GEMINI_API_KEY", ["GOOGLE_API_KEY"])
    if g:
        set_env("GEMINI_API_KEY", g)
        set_env("GOOGLE_API_KEY", g)

    w = _coalesce_env("WOLFRAM_APP_ID", ["WOLFRAM_APPID"])
    if w:
        set_env("WOLFRAM_APP_ID", w)
        set_env("WOLFRAM_APPID", w)

    tkey = _coalesce_env("TOKENC_API_KEY", [])
    if tkey:
        set_env("TOKENC_API_KEY", tkey)

    return {
        "gemini_api_key_set": bool(_coalesce_env("GEMINI_API_KEY", ["GOOGLE_API_KEY"])),
        "wolfram_app_id_set": bool(_coalesce_env("WOLFRAM_APP_ID", ["WOLFRAM_APPID"])),
        "tokenc_api_key_set": bool(_coalesce_env("TOKENC_API_KEY", [])),
    }


def _main() -> None:
    status = initialize_env_vars()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    _main()
