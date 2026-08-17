import tempfile
import unittest
from pathlib import Path

import yaml

from config import ConfigError, get_active_credentials, load_config, mask_secret


SAMPLE = {
    "mode": "demo",
    "demo": {
        "appkey": "demo-key-1234",
        "secretkey": "demo-secret-5678",
        "account": "50123456",
        "base_url": "https://mockapi.kiwoom.com",
        "ws_url": "wss://mockapi.kiwoom.com:10000",
    },
    "real": {
        "appkey": "real-key",
        "secretkey": "real-secret",
        "account": "12345678",
        "base_url": "https://api.kiwoom.com",
        "ws_url": "wss://api.kiwoom.com:10000",
    },
}


class ConfigTests(unittest.TestCase):
    def _write(self, data: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        with handle as fh:
            yaml.safe_dump(data, fh, allow_unicode=True)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_load_repo_config_file(self):
        data = load_config()
        self.assertEqual(data.get("mode"), "demo")
        self.assertIn("demo", data)
        self.assertIn("appkey", data["demo"])
        self.assertIn("secretkey", data["demo"])

    def test_reads_demo_credentials_from_config(self):
        path = self._write(SAMPLE)
        creds = get_active_credentials(path)
        self.assertEqual(creds["mode"], "demo")
        self.assertEqual(creds["appkey"], "demo-key-1234")
        self.assertEqual(creds["secretkey"], "demo-secret-5678")
        self.assertEqual(creds["account"], "50123456")
        self.assertEqual(creds["base_url"], "https://mockapi.kiwoom.com")

    def test_reads_real_credentials_when_mode_is_real(self):
        data = dict(SAMPLE)
        data["mode"] = "real"
        path = self._write(data)
        creds = get_active_credentials(path)
        self.assertEqual(creds["mode"], "real")
        self.assertEqual(creds["appkey"], "real-key")
        self.assertEqual(creds["secretkey"], "real-secret")

    def test_missing_demo_keys_raise(self):
        data = dict(SAMPLE)
        data["demo"] = dict(SAMPLE["demo"])
        data["demo"]["appkey"] = ""
        data["demo"]["secretkey"] = ""
        path = self._write(data)
        with self.assertRaises(ConfigError) as ctx:
            get_active_credentials(path)
        self.assertIn("appkey", str(ctx.exception))
        self.assertIn("secretkey", str(ctx.exception))

    def test_mask_secret_hides_value(self):
        self.assertEqual(mask_secret("abcd1234"), "abcd****")
        self.assertEqual(mask_secret(""), "(비어 있음)")


if __name__ == "__main__":
    unittest.main()
