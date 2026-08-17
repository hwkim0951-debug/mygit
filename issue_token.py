"""Issue a Kiwoom REST API access token from config.yaml."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from config import CONFIG_PATH, ConfigError, get_active_credentials, mask_secret

TOKEN_PATH = "/oauth2/token"
TOKEN_CACHE = Path(__file__).resolve().parent / "token.json"
KST = timezone(timedelta(hours=9))
REFRESH_MARGIN = timedelta(minutes=10)


class TokenError(RuntimeError):
    """Raised when Kiwoom token issuance fails."""


def _hint_for_failure(return_code: object, return_msg: str, mode: str, config_path: Path) -> str:
    text = str(return_msg)
    if "8001" in text or "8002" in text:
        return (
            f"이 오류는 {config_path} 에서 읽은 키가 키움 모의투자 앱과 다를 때 납니다. "
            "OpenAPI 포털의 모의투자 앱에서 appkey/secretkey를 다시 복사하세요. "
            "키체인·암호화된 값·실전 키를 쓰면 8001이 납니다."
        )
    if "8030" in text:
        env = "모의투자(demo)" if mode == "demo" else "실전투자(real)"
        return (
            f"지금 mode는 {env} 인데, 넣은 키가 다른 환경 키입니다. "
            "모의투자 키는 mockapi, 실전 키는 api.kiwoom.com 과 짝이 맞아야 합니다."
        )
    if return_code not in (None, 0):
        return f"키움 응답 return_code={return_code}. URL과 키 종류를 다시 확인하세요."
    return text


def _parse_expiry(value: str) -> datetime:
    parsed = datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    return parsed


def load_cached_token(*, mode: str, base_url: str) -> dict | None:
    if not TOKEN_CACHE.is_file():
        return None
    try:
        record = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict) or not record.get("token"):
        return None
    if record.get("mode") != mode or record.get("base_url") != base_url:
        return None
    expires_dt = record.get("expires_dt")
    if not expires_dt:
        return None
    try:
        expires_at = _parse_expiry(str(expires_dt))
    except ValueError:
        return None
    if datetime.now(KST) >= expires_at - REFRESH_MARGIN:
        return None
    return record


def issue_token(
    path: Path | str = CONFIG_PATH,
    *,
    timeout_seconds: int = 20,
    force: bool = False,
) -> dict:
    config_path = Path(path)
    creds = get_active_credentials(config_path)
    if not force:
        cached = load_cached_token(mode=creds["mode"], base_url=creds["base_url"])
        if cached is not None:
            cached["from_cache"] = True
            return cached

    url = creds["base_url"].rstrip("/") + TOKEN_PATH
    response = requests.post(
        url,
        json={
            "grant_type": "client_credentials",
            "appkey": creds["appkey"],
            "secretkey": creds["secretkey"],
        },
        headers={"Content-Type": "application/json;charset=UTF-8"},
        timeout=timeout_seconds,
    )
    try:
        data = response.json()
    except ValueError as exc:
        raise TokenError(f"토큰 응답이 JSON이 아닙니다. HTTP {response.status_code}") from exc

    if not isinstance(data, dict):
        raise TokenError("토큰 응답 형식이 올바르지 않습니다.")

    return_code = data.get("return_code")
    return_msg = str(data.get("return_msg") or "")
    if response.status_code >= 400 or return_code not in (None, 0):
        hint = _hint_for_failure(return_code, return_msg, creds["mode"], config_path)
        raise TokenError(
            f"모의투자 토큰 발급 실패(return_code={return_code}): {return_msg}\n"
            f"설정 파일: {config_path}\n요청 URL : {url}\n"
            f"appkey {len(creds['appkey'])}자 / secretkey {len(creds['secretkey'])}자\n{hint}"
            if creds["mode"] == "demo"
            else f"실전투자 토큰 발급 실패(return_code={return_code}): {return_msg}\n{hint}"
        )

    token = data.get("token")
    if not token:
        raise TokenError("토큰 응답에 token 값이 없습니다.")

    record = {
        "mode": creds["mode"],
        "token_type": data.get("token_type") or "bearer",
        "expires_dt": data.get("expires_dt"),
        "token": token,
        "base_url": creds["base_url"],
        "from_cache": False,
    }
    TOKEN_CACHE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


if __name__ == "__main__":
    force = "--force" in sys.argv
    try:
        creds = get_active_credentials()
        print(f"설정 파일: {CONFIG_PATH}")
        print(f"요청 URL : {creds['base_url'].rstrip('/')}{TOKEN_PATH}")
        print(f"appkey   : {len(creds['appkey'])}자 {mask_secret(creds['appkey'])}")
        print(f"secretkey: {len(creds['secretkey'])}자 {mask_secret(creds['secretkey'])}")
        record = issue_token(force=force)
    except (ConfigError, TokenError) as exc:
        print(f"[토큰 오류] {exc}")
        raise SystemExit(1) from exc

    label = "모의투자" if record["mode"] == "demo" else "실전투자"
    source = "기존 토큰 재사용" if record.get("from_cache") else "신규 발급"
    print(f"토큰 발급 성공 ({label}, {source})")
    print(f"token     : {mask_secret(str(record['token']), visible=8)}")
    print(f"만료      : {record.get('expires_dt') or '(없음)'}")
    print(f"저장 위치 : {TOKEN_CACHE}")
