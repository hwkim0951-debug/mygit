import json
import unittest
from unittest.mock import patch

from issue_token import TokenError, issue_token


class IssueTokenTests(unittest.TestCase):
    def test_success_saves_token(self):
        creds = {
            "mode": "demo",
            "appkey": "demo-key",
            "secretkey": "demo-secret",
            "account": "",
            "base_url": "https://mockapi.kiwoom.com",
            "ws_url": "",
        }
        payload = {
            "return_code": 0,
            "return_msg": "정상적으로 처리되었습니다",
            "token": "abc123token",
            "token_type": "bearer",
            "expires_dt": "20260818200000",
        }
        with (
            patch("issue_token.get_active_credentials", return_value=creds),
            patch("issue_token.requests.post") as post,
            patch("issue_token.TOKEN_CACHE") as cache,
            patch("issue_token.load_cached_token", return_value=None),
        ):
            post.return_value.status_code = 200
            post.return_value.json.return_value = payload
            record = issue_token(force=True)

        self.assertEqual(record["token"], "abc123token")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://mockapi.kiwoom.com/oauth2/token")
        self.assertEqual(kwargs["json"]["appkey"], "demo-key")
        self.assertEqual(kwargs["json"]["secretkey"], "demo-secret")
        cache.write_text.assert_called_once()
        saved = json.loads(cache.write_text.call_args.args[0])
        self.assertEqual(saved["token"], "abc123token")

    def test_8001_raises_token_error(self):
        creds = {
            "mode": "demo",
            "appkey": "bad",
            "secretkey": "bad",
            "account": "",
            "base_url": "https://mockapi.kiwoom.com",
            "ws_url": "",
        }
        payload = {
            "return_code": 3,
            "return_msg": "인증에 실패했습니다[8001:App Key와 Secret Key 검증에 실패했습니다]",
        }
        with (
            patch("issue_token.get_active_credentials", return_value=creds),
            patch("issue_token.requests.post") as post,
        ):
            post.return_value.status_code = 200
            post.return_value.json.return_value = payload
            with self.assertRaises(TokenError) as ctx:
                issue_token(force=True)
        self.assertIn("8001", str(ctx.exception))
        self.assertIn("모의투자 앱", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
