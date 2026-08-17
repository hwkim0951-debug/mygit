"""Issue a Kiwoom REST API access token from config.yaml."""

from __future__ import annotations

import json
from pathlib import Path

import requests

from config import CONFIG_PATH, ConfigError, get_active_credentials, mask_secret

TOKEN_PATH = "/oauth2/token"
TOKEN_CACHE = Path(__file__).resolve().parent / "token.json"


class TokenError(RuntimeError):
    """Raised when Kiwoom token issuance fails."""


def _hint_for_failure(return_code: object, return_msg: str, mode: str) -> str:
    text = str(return_msg)
    if "8001" in text or "8002" in text:
        return (
            "config.yaml 의 키가 키움 서버에서 거부되었습니다. "
            "OpenAPI 포털에서 모의투자 앱의 appkey/secretkey를 다시 복사해 주세요. "
            "암호화된 값이나 실전 키를 넣으면 이 오류가 납니다."
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


def issue_token(path: Path | str = CONFIG_PATH, *, timeout_seconds: int = 20) -> dict:
    creds = get_active_credentials(path)
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
        hint = _hint_for_failure(return_code, return_msg, creds["mode"])
        raise TokenError(
            f"모의투자 토큰 발급 실패(return_code={return_code}): {return_msg}\n{hint}"
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
    }
    TOKEN_CACHE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


if __name__ == "__main__":
    try:
        record = issue_token()
    except (ConfigError, TokenError) as exc:
        print(f"[토큰 오류] {exc}")
        raise SystemExit(1) from exc

    label = "모의투자" if record["mode"] == "demo" else "실전투자"
    print(f"토큰 발급 성공 ({label})")
    print(f"token     : {mask_secret(str(record['token']), visible=8)}")
    print(f"만료      : {record.get('expires_dt') or '(없음)'}")
    print(f"저장 위치 : {TOKEN_CACHE}")
