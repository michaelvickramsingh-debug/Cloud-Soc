"""
Lambda Function: Parse CloudTrail Logs
Triggered by S3 events when CloudTrail logs arrive
Sends parsed logs to CloudGuard backend for processing
"""

import gzip
import io
import json
import logging
import os
from datetime import datetime
from urllib.parse import unquote_plus, urlparse
from urllib.request import Request, urlopen

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
BATCH_SIZE = 100
TIMEOUT = 30


def get_s3_client():
    """Create the S3 client only when the Lambda processes an event."""
    import boto3

    return boto3.client('s3')


def get_secrets_manager_client():
    """Create the Secrets Manager client only when it is needed."""
    import boto3

    return boto3.client('secretsmanager')


def get_cloudguard_api():
    """Return the explicitly configured backend ingestion endpoint."""
    api_url = os.environ.get('CLOUDGUARD_API')
    parsed_url = urlparse(api_url) if api_url else None
    if not parsed_url or parsed_url.scheme != 'https' or not parsed_url.netloc:
        raise RuntimeError(
            'CLOUDGUARD_API must be an absolute HTTPS /api/logs/ingest endpoint'
        )
    return api_url


def get_ingest_headers():
    """Return the required authentication header for the ingestion endpoint."""
    api_key = os.environ.get('CLOUDGUARD_API_KEY')
    if not api_key:
        secret_arn = os.environ.get('CLOUDGUARD_API_KEY_SECRET_ARN')
        if secret_arn:
            api_key = get_secrets_manager_client().get_secret_value(
                SecretId=secret_arn
            )['SecretString']
    if not api_key:
        raise RuntimeError(
            'CLOUDGUARD_API_KEY or CLOUDGUARD_API_KEY_SECRET_ARN must be configured'
        )
    return {
        'Content-Type': 'application/json',
        'X-CloudGuard-API-Key': api_key,
    }


def get_s3_records(event):
    """Normalize direct S3 and EventBridge S3 Object Created events."""
    records = event.get('Records')
    if records is not None:
        return records

    if event.get('source') == 'aws.s3' and event.get('detail-type') == 'Object Created':
        detail = event.get('detail', {})
        bucket = detail.get('bucket', {}).get('name')
        key = detail.get('object', {}).get('key')
        if bucket and key:
            return [{
                's3': {
                    'bucket': {'name': bucket},
                    'object': {'key': key},
                }
            }]

    raise ValueError('Expected an S3 Object Created event')


def lambda_handler(event, context):
    """
    Main Lambda handler
    Triggered by S3:ObjectCreated events for CloudTrail logs
    """
    records = get_s3_records(event)
    logger.info("Received %d S3 record(s)", len(records))
    get_cloudguard_api()
    get_ingest_headers()
    processed_count = 0

    for record in records:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        logger.info("Processing s3://%s/%s", bucket, key)

        logs = download_and_parse_logs(bucket, key)
        if not logs:
            logger.warning("No logs found in %s", key)
            continue

        count = send_logs_to_backend(logs)
        processed_count += count
        logger.info("Sent %d logs to CloudGuard", count)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'CloudTrail logs processed',
            'processed': processed_count,
            'failed': 0
        })
    }


def download_and_parse_logs(bucket, key):
    """
    Download CloudTrail log from S3 and decompress
    CloudTrail logs are gzipped JSON files
    """
    logger.info("Downloading s3://%s/%s", bucket, key)
    response = get_s3_client().get_object(Bucket=bucket, Key=key)

    with gzip.GzipFile(fileobj=io.BytesIO(response['Body'].read())) as gzipfile:
        content = gzipfile.read().decode('utf-8')
        data = json.loads(content)

    logs = data.get('Records', [])
    logger.info("Parsed %d events from CloudTrail log", len(logs))
    return logs


def send_logs_to_backend(logs):
    """
    Send parsed logs to CloudGuard backend
    Sends in batches to avoid timeouts
    """
    total_sent = 0

    for i in range(0, len(logs), BATCH_SIZE):
        batch = logs[i:i+BATCH_SIZE]

        payload = {
            'logs': batch,
            'source': 'cloudtrail',
            'timestamp': datetime.utcnow().isoformat(),
            'batch_number': i // BATCH_SIZE,
            'total_batches': (len(logs) + BATCH_SIZE - 1) // BATCH_SIZE
        }

        logger.info("Sending batch %d: %d logs", i // BATCH_SIZE + 1, len(batch))
        request = Request(
            get_cloudguard_api(),
            data=json.dumps(payload).encode('utf-8'),
            headers=get_ingest_headers(),
            method='POST',
        )

        with urlopen(request, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode('utf-8'))

        sent = result.get('count', len(batch))
        total_sent += sent
        logger.info("Successfully sent %d logs", sent)

    return total_sent


def parse_log_entry(log_entry):
    """
    Extract relevant fields from CloudTrail log entry
    """
    user_identity = log_entry.get('userIdentity', {})
    request_params = log_entry.get('requestParameters', {})

    return {
        'timestamp': log_entry.get('eventTime'),
        'user': user_identity.get('userName', 'unknown'),
        'user_type': user_identity.get('type', 'unknown'),
        'principal_id': user_identity.get('principalId', 'unknown'),
        'event': log_entry.get('eventName'),
        'source': log_entry.get('eventSource'),
        'ip': log_entry.get('sourceIPAddress'),
        'region': log_entry.get('awsRegion'),
        'user_agent': log_entry.get('userAgent'),
        'status': 'success' if log_entry.get('errorCode') is None else 'error',
        'error_code': log_entry.get('errorCode'),
        'error_message': log_entry.get('errorMessage'),
        'resource': request_params.get('bucketName') or request_params.get('instanceId') or 'unknown',
        'raw': json.dumps(log_entry)
    }
