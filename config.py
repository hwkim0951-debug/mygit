"""Load trading credentials from config.yaml."""

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


def get_active_credentials(path: Path | str = CONFIG_PATH) -> dict[str, str]:
    """Return App Key / App Secret for the mode set in config.yaml."""
    data = load_config(path)
    mode = str(data.get("mode") or "paper").strip().lower()
    if mode not in {"paper", "real"}:
        raise ConfigError(f"지원하지 않는 mode 입니다: {mode!r} (paper 또는 real)")

    section = data.get(mode)
    if not isinstance(section, dict):
        raise ConfigError(f"config.yaml 에 '{mode}' 항목이 없습니다.")

    app_key = str(section.get("app_key") or "").strip()
    app_secret = str(section.get("app_secret") or "").strip()
    account = str(section.get("account") or "").strip().replace("-", "")
    account_product_code = str(section.get("account_product_code") or "01").strip()
    base_url = str(section.get("base_url") or "").strip()

    missing = [
        name
        for name, value in (
            ("app_key", app_key),
            ("app_secret", app_secret),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(
            f"모의투자 인증값이 비어 있습니다. config.yaml 의 {mode}.{joined} 를 채워 주세요."
            if mode == "paper"
            else f"실전투자 인증값이 비어 있습니다. config.yaml 의 {mode}.{joined} 를 채워 주세요."
        )

    return {
        "mode": mode,
        "app_key": app_key,
        "app_secret": app_secret,
        "account": account,
        "account_product_code": account_product_code,
        "base_url": base_url,
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

    label = "모의투자" if creds["mode"] == "paper" else "실전투자"
    print(f"현재 mode: {creds['mode']} ({label})")
    print(f"App Key   : {mask_secret(creds['app_key'])}")
    print(f"App Secret: {mask_secret(creds['app_secret'])}")
    print(f"계좌번호  : {creds['account'] or '(미입력)'}")
    print(f"API URL   : {creds['base_url']}")
