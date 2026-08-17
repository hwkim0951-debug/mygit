import tempfile
import unittest
from pathlib import Path

import yaml

from config import ConfigError, get_active_credentials, load_config, mask_secret


SAMPLE = {
    "mode": "paper",
    "paper": {
        "app_key": "paper-key-1234",
        "app_secret": "paper-secret-5678",
        "account": "50123456",
        "account_product_code": "01",
        "base_url": "https://openapivts.koreainvestment.com:29443",
    },
    "real": {
        "app_key": "real-key",
        "app_secret": "real-secret",
        "account": "12345678",
        "account_product_code": "01",
        "base_url": "https://openapi.koreainvestment.com:9443",
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
        self.assertEqual(data.get("mode"), "paper")
        self.assertIn("paper", data)
        self.assertIn("app_key", data["paper"])
        self.assertIn("app_secret", data["paper"])

    def test_reads_paper_credentials_from_config(self):
        path = self._write(SAMPLE)
        creds = get_active_credentials(path)
        self.assertEqual(creds["mode"], "paper")
        self.assertEqual(creds["app_key"], "paper-key-1234")
        self.assertEqual(creds["app_secret"], "paper-secret-5678")
        self.assertEqual(creds["account"], "50123456")

    def test_reads_real_credentials_when_mode_is_real(self):
        data = dict(SAMPLE)
        data["mode"] = "real"
        path = self._write(data)
        creds = get_active_credentials(path)
        self.assertEqual(creds["mode"], "real")
        self.assertEqual(creds["app_key"], "real-key")
        self.assertEqual(creds["app_secret"], "real-secret")

    def test_missing_paper_keys_raise(self):
        data = dict(SAMPLE)
        data["paper"] = dict(SAMPLE["paper"])
        data["paper"]["app_key"] = ""
        data["paper"]["app_secret"] = ""
        path = self._write(data)
        with self.assertRaises(ConfigError) as ctx:
            get_active_credentials(path)
        self.assertIn("app_key", str(ctx.exception))
        self.assertIn("app_secret", str(ctx.exception))

    def test_mask_secret_hides_value(self):
        self.assertEqual(mask_secret("abcd1234"), "abcd****")
        self.assertEqual(mask_secret(""), "(비어 있음)")


if __name__ == "__main__":
    unittest.main()
