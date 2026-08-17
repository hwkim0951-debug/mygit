"""Load Kiwoom REST API credentials from config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


class ConfigError(ValueError):
    """Raised when required config values are missing or invalid."""


def load_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"설정 파일이 없습니다: {config_path}")

    with config_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ConfigError("config.yaml 형식이 올바르지 않습니다.")
    return data


def _first_nonempty(section: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(section.get(key) or "").strip()
        if value:
            return value
    return ""


def get_active_credentials(path: Path | str = CONFIG_PATH) -> dict[str, str]:
    """Return appkey / secretkey for the mode set in config.yaml."""
    data = load_config(path)
    mode = str(data.get("mode") or "demo").strip().lower()
    if mode == "paper":
        mode = "demo"
    if mode not in {"demo", "real"}:
        raise ConfigError(f"지원하지 않는 mode 입니다: {mode!r} (demo 또는 real)")

    section = data.get(mode)
    if not isinstance(section, dict):
        raise ConfigError(f"config.yaml 에 '{mode}' 항목이 없습니다.")

    appkey = _first_nonempty(section, "appkey", "app_key")
    secretkey = _first_nonempty(section, "secretkey", "app_secret", "secret_key")
    account = str(section.get("account") or "").strip().replace("-", "")
    base_url = str(section.get("base_url") or "").strip()
    ws_url = str(section.get("ws_url") or "").strip()

    missing = [
        name
        for name, value in (
            ("appkey", appkey),
            ("secretkey", secretkey),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        label = "모의투자" if mode == "demo" else "실전투자"
        raise ConfigError(
            f"{label} 인증값이 비어 있습니다. config.yaml 의 {mode}.{joined} 를 채워 주세요."
        )

    return {
        "mode": mode,
        "appkey": appkey,
        "secretkey": secretkey,
        "account": account,
        "base_url": base_url,
        "ws_url": ws_url,
    }


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return "(비어 있음)"
    if len(value) <= visible:
        return "*" * len(value)
    return value[:visible] + "*" * (len(value) - visible)


if __name__ == "__main__":
    try:
        creds = get_active_credentials()
    except ConfigError as exc:
        print(f"[설정 오류] {exc}")
        raise SystemExit(1) from exc

    label = "모의투자" if creds["mode"] == "demo" else "실전투자"
    print(f"현재 mode : {creds['mode']} ({label})")
    print(f"appkey    : {mask_secret(creds['appkey'])}")
    print(f"secretkey : {mask_secret(creds['secretkey'])}")
    print(f"계좌번호  : {creds['account'] or '(미입력)'}")
    print(f"API URL   : {creds['base_url']}")
