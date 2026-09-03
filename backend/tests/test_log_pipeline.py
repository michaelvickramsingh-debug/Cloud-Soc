"""
backend/tests/test_log_pipeline.py
Integration tests for end-to-end log ingestion and streaming
"""

import pytest
import json
from datetime import datetime
from database.database import init_db, reset_db
from services.log_ingestion import LogIngestionService, parse_cloudtrail_log
from services.detection import detect_threat_from_log
from routes.live_logs import broadcast_new_logs, broadcast_new_alert


@pytest.fixture(autouse=True)
def fresh_db():
    """Start every test with a clean, schema-initialised database.

    Without this, tests that exercise LogIngestionService (which reads and
    writes the alerts/cloud_logs tables) fail with "no such table" because
    nothing else in this file ever calls init_db().
    """
    init_db()
    reset_db()
    yield
    reset_db()


class TestLogParsing:
    """Test log parsing from different sources"""

    def test_parse_cloudtrail_log(self):
        """Test CloudTrail log parsing"""
        cloudtrail_event = {
            "eventTime": "2024-08-27T10:15:30Z",
            "userIdentity": {
                "type": "IAMUser",
                "userName": "alice",
                "principalId": "AIDAI123456789EXAMPLE"
            },
            "eventName": "GetObject",
            "eventSource": "s3.amazonaws.com",
            "sourceIPAddress": "203.0.113.45",
            "awsRegion": "us-east-1",
            "userAgent": "aws-cli/2.0.0",
            "requestParameters": {
                "bucketName": "my-bucket"
            }
        }

        log_record = parse_cloudtrail_log(cloudtrail_event)

        assert log_record['timestamp'] == "2024-08-27T10:15:30Z"
        assert log_record['user'] == "alice"
        assert log_record['event'] == "GetObject"
        assert log_record['source'] == "s3.amazonaws.com"
        assert log_record['ip'] == "203.0.113.45"
        assert log_record['region'] == "us-east-1"
        assert log_record['status'] == "success"
        assert log_record['resource'] == "my-bucket"

    def test_parse_cloudtrail_log_with_error(self):
        """Test CloudTrail log with error code"""
        cloudtrail_event = {
            "eventTime": "2024-08-27T10:20:00Z",
            "userIdentity": {
                "type": "IAMUser",
                "userName": "bob"
            },
            "eventName": "PutObject",
            "eventSource": "s3.amazonaws.com",
            "sourceIPAddress": "192.0.2.10",
            "awsRegion": "us-west-2",
            "errorCode": "UnauthorizedOperation",
            "errorMessage": "User is not authorized to access this bucket"
        }

        log_record = parse_cloudtrail_log(cloudtrail_event)

        assert log_record['status'] == "error"
        assert log_record['error_code'] == "UnauthorizedOperation"


class TestThreatDetection:
    """Test threat detection on logs"""

    def test_detect_privilege_escalation(self):
        """Test detection of privilege escalation"""
        log = {
            'event': 'PutUserPolicy',
            'user': 'alice',
            'ip': '203.0.113.45'
        }

        severity, reasons = detect_threat_from_log(log)

        assert severity == 'Critical'
        assert len(reasons) > 0
        assert any('privilege' in reason.lower() for reason in reasons)

    def test_detect_unauthorized_access(self):
        """Test detection of unauthorized access"""
        log = {
            'event': 'GetObject',
            'error_code': 'UnauthorizedOperation',
            'status': 'error'
        }

        severity, reasons = detect_threat_from_log(log)

        assert severity == 'High'

    def test_detect_multiple_threats(self):
        """Test log that triggers multiple rules"""
        log = {
            'event': 'DeleteBucket',  # Matches data deletion
            'user': 'root',           # Matches root activity
            'ip': '203.0.113.45'
        }

        severity, reasons = detect_threat_from_log(log)

        assert severity == 'Critical'
        assert len(reasons) >= 2

    def test_benign_log_no_threat(self):
        """Test benign log doesn't trigger alerts"""
        log = {
            'event': 'DescribeInstances',
            'user': 'alice',
            'ip': '192.168.1.100'  # Internal IP
        }

        severity, reasons = detect_threat_from_log(log)

        assert severity is None
        assert len(reasons) == 0


class TestLogIngestion:
    """Test log ingestion service"""

    def test_ingest_batch_of_logs(self):
        """Test ingesting a batch of CloudTrail logs"""
        logs = [
            {
                "eventTime": "2024-08-27T10:15:30Z",
                "userIdentity": {"userName": "alice", "type": "IAMUser"},
                "eventName": "GetObject",
                "eventSource": "s3.amazonaws.com",
                "sourceIPAddress": "203.0.113.45",
                "awsRegion": "us-east-1",
                "requestParameters": {"bucketName": "data-bucket"}
            },
            {
                "eventTime": "2024-08-27T10:15:45Z",
                "userIdentity": {"userName": "bob", "type": "IAMUser"},
                "eventName": "PutUserPolicy",
                "eventSource": "iam.amazonaws.com",
                "sourceIPAddress": "203.0.113.50",
                "awsRegion": "us-east-1"
            }
        ]

        stats = LogIngestionService.ingest_logs(logs, source='cloudtrail')

        assert stats['total'] == 2
        assert stats['processed'] > 0
        assert stats['errors'] == 0
        assert stats['alerts'] >= 1  # At least PutUserPolicy detected as threat

    def test_ingest_with_error_recovery(self):
        """Test that ingestion continues even if one log fails"""
        logs = [
            {  # Valid log
                "eventTime": "2024-08-27T10:15:30Z",
                "userIdentity": {"userName": "alice"},
                "eventName": "GetObject",
                "eventSource": "s3.amazonaws.com",
                "sourceIPAddress": "203.0.113.45",
                "awsRegion": "us-east-1"
            },
            # Missing required fields will test error handling
            {},
            {  # Another valid log
                "eventTime": "2024-08-27T10:15:50Z",
                "userIdentity": {"userName": "charlie"},
                "eventName": "ListBuckets",
                "eventSource": "s3.amazonaws.com",
                "sourceIPAddress": "203.0.113.55",
                "awsRegion": "us-east-1"
            }
        ]

        stats = LogIngestionService.ingest_logs(logs, source='cloudtrail')

        # Should process valid logs despite one failure
        assert stats['total'] == 3
        assert stats['errors'] >= 1
        assert stats['processed'] >= 2


class TestLogFormat:
    """Test log format transformation"""

    def test_log_preserves_original_data(self):
        """Test that raw log data is preserved"""
        original = {
            "eventTime": "2024-08-27T10:15:30Z",
            "userIdentity": {"userName": "alice"},
            "eventName": "DescribeInstances",
            "eventSource": "ec2.amazonaws.com",
            "sourceIPAddress": "203.0.113.45",
            "awsRegion": "us-east-1"
        }

        log_record = parse_cloudtrail_log(original)

        assert 'raw' in log_record
        assert json.loads(log_record['raw']) == original

    def test_log_has_required_fields(self):
        """Test log record has all required fields"""
        original = {
            "eventTime": "2024-08-27T10:15:30Z",
            "userIdentity": {"userName": "alice"},
            "eventName": "GetObject",
            "eventSource": "s3.amazonaws.com",
            "sourceIPAddress": "203.0.113.45",
            "awsRegion": "us-east-1",
            "userAgent": "aws-cli",
            "requestParameters": {}
        }

        log_record = parse_cloudtrail_log(original)

        required_fields = ['timestamp', 'user', 'event', 'source', 'ip', 'region', 'status', 'raw']
        for field in required_fields:
            assert field in log_record


# Integration test scenarios
class TestEndToEnd:
    """End-to-end integration tests"""

    def test_suspicious_activity_flow(self):
        """Test full flow: CloudTrail → Parse → Detect → Alert"""
        # Step 1: Simulate CloudTrail log with suspicious activity
        suspicious_logs = [
            {
                "eventTime": "2024-08-27T10:30:00Z",
                "userIdentity": {"userName": "attacker", "type": "IAMUser"},
                "eventName": "PutUserPolicy",
                "eventSource": "iam.amazonaws.com",
                "sourceIPAddress": "198.51.100.45",
                "awsRegion": "us-east-1"
            },
            {
                "eventTime": "2024-08-27T10:30:15Z",
                "userIdentity": {"userName": "attacker"},
                "eventName": "CreateAccessKey",
                "eventSource": "iam.amazonaws.com",
                "sourceIPAddress": "198.51.100.45",
                "awsRegion": "us-east-1"
            }
        ]

        # Step 2: Ingest logs (in real scenario, Lambda calls this)
        stats = LogIngestionService.ingest_logs(suspicious_logs, source='cloudtrail')

        # Step 3: Verify alerts were generated
        assert stats['alerts'] >= 2, f"Expected at least 2 alerts, got {stats['alerts']}"
        assert stats['errors'] == 0
        print(f"Integration test passed: {stats}")

    def test_batch_processing(self):
        """Test batch processing of large log volume"""
        # Simulate 250 logs (will be split into 3 batches of 100)
        logs = [
            {
                "eventTime": f"2024-08-27T10:{i:02d}:00Z",
                "userIdentity": {"userName": f"user{i}", "type": "IAMUser"},
                "eventName": "GetObject" if i % 3 == 0 else "ListBuckets",
                "eventSource": "s3.amazonaws.com",
                "sourceIPAddress": f"203.0.113.{i % 255}",
                "awsRegion": "us-east-1" if i % 2 == 0 else "us-west-2",
                "requestParameters": {"bucketName": f"bucket-{i}"}
            }
            for i in range(250)
        ]

        stats = LogIngestionService.ingest_logs(logs, source='cloudtrail')

        assert stats['total'] == 250
        assert stats['processed'] <= 250
        assert stats['errors'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
