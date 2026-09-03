import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "lambda" / "parse_cloudtrail.py"
SPEC = importlib.util.spec_from_file_location("parse_cloudtrail", MODULE_PATH)
parse_cloudtrail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parse_cloudtrail)


class LambdaParserTests(unittest.TestCase):
    def setUp(self):
        self.previous_api_url = parse_cloudtrail.os.environ.get("CLOUDGUARD_API")
        parse_cloudtrail.os.environ["CLOUDGUARD_API"] = (
            "https://api.example.test/api/logs/ingest"
        )
        self.previous_api_key = parse_cloudtrail.os.environ.get("CLOUDGUARD_API_KEY")
        parse_cloudtrail.os.environ["CLOUDGUARD_API_KEY"] = "test-api-key"

    def tearDown(self):
        if self.previous_api_url is None:
            parse_cloudtrail.os.environ.pop("CLOUDGUARD_API", None)
        else:
            parse_cloudtrail.os.environ["CLOUDGUARD_API"] = self.previous_api_url
        if self.previous_api_key is None:
            parse_cloudtrail.os.environ.pop("CLOUDGUARD_API_KEY", None)
        else:
            parse_cloudtrail.os.environ["CLOUDGUARD_API_KEY"] = self.previous_api_key

    def test_lambda_handler_decodes_s3_key_and_processes_logs(self):
        captured = {}
        original_download = parse_cloudtrail.download_and_parse_logs
        original_send = parse_cloudtrail.send_logs_to_backend

        def download_logs(bucket, key):
            captured["location"] = (bucket, key)
            return [{"eventName": "GetObject"}]

        parse_cloudtrail.download_and_parse_logs = download_logs
        parse_cloudtrail.send_logs_to_backend = lambda logs: len(logs)
        self.addCleanup(
            setattr, parse_cloudtrail, "download_and_parse_logs", original_download
        )
        self.addCleanup(
            setattr, parse_cloudtrail, "send_logs_to_backend", original_send
        )

        result = parse_cloudtrail.lambda_handler(
            {
                "Records": [
                    {
                        "s3": {
                            "bucket": {"name": "cloudtrail-logs"},
                            "object": {"key": "AWSLogs%2Faccount%2Flog+file.json.gz"},
                        }
                    }
                ]
            },
            None,
        )

        self.assertEqual(
            captured["location"],
            ("cloudtrail-logs", "AWSLogs/account/log file.json.gz"),
        )
        self.assertEqual(json.loads(result["body"])["processed"], 1)

    def test_lambda_handler_requires_https_backend_endpoint(self):
        parse_cloudtrail.os.environ.pop("CLOUDGUARD_API")

        with self.assertRaisesRegex(RuntimeError, "CLOUDGUARD_API"):
            parse_cloudtrail.lambda_handler({"Records": []}, None)

    def test_lambda_handler_accepts_eventbridge_s3_event(self):
        captured = {}
        original_download = parse_cloudtrail.download_and_parse_logs
        original_send = parse_cloudtrail.send_logs_to_backend

        def download_logs(bucket, key):
            captured["location"] = (bucket, key)
            return [{"eventName": "GetObject"}]

        parse_cloudtrail.download_and_parse_logs = download_logs
        parse_cloudtrail.send_logs_to_backend = lambda logs: len(logs)
        self.addCleanup(
            setattr, parse_cloudtrail, "download_and_parse_logs", original_download
        )
        self.addCleanup(
            setattr, parse_cloudtrail, "send_logs_to_backend", original_send
        )

        result = parse_cloudtrail.lambda_handler(
            {
                "source": "aws.s3",
                "detail-type": "Object Created",
                "detail": {
                    "bucket": {"name": "cloudtrail-logs"},
                    "object": {"key": "AWSLogs/account/CloudTrail/log.json.gz"},
                },
            },
            None,
        )

        self.assertEqual(
            captured["location"],
            ("cloudtrail-logs", "AWSLogs/account/CloudTrail/log.json.gz"),
        )
        self.assertEqual(json.loads(result["body"])["processed"], 1)

    def test_ingest_headers_load_api_key_from_secrets_manager(self):
        parse_cloudtrail.os.environ.pop("CLOUDGUARD_API_KEY")
        parse_cloudtrail.os.environ["CLOUDGUARD_API_KEY_SECRET_ARN"] = (
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:ingest-key"
        )

        class SecretsManagerClient:
            def get_secret_value(self, SecretId):
                self.secret_id = SecretId
                return {"SecretString": "secret-api-key"}

        client = SecretsManagerClient()
        original_client_factory = parse_cloudtrail.get_secrets_manager_client
        parse_cloudtrail.get_secrets_manager_client = lambda: client
        self.addCleanup(
            setattr,
            parse_cloudtrail,
            "get_secrets_manager_client",
            original_client_factory,
        )
        self.addCleanup(
            parse_cloudtrail.os.environ.pop,
            "CLOUDGUARD_API_KEY_SECRET_ARN",
            None,
        )

        self.assertEqual(
            parse_cloudtrail.get_ingest_headers()["X-CloudGuard-API-Key"],
            "secret-api-key",
        )
        self.assertEqual(
            client.secret_id,
            "arn:aws:secretsmanager:us-east-1:123456789012:secret:ingest-key",
        )
