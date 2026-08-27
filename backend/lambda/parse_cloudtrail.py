"""
Lambda Function: Parse CloudTrail Logs
Triggered by S3 events when CloudTrail logs arrive
Sends parsed logs to CloudGuard backend for processing
"""

import json
import boto3
import requests
import gzip
import io
import logging
from datetime import datetime
from urllib.parse import quote

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3 = boto3.client('s3')

# Configuration
CLOUDGUARD_API = 'http://backend:5001/api/logs/ingest'  # Update with your backend URL
BATCH_SIZE = 100
TIMEOUT = 30


def lambda_handler(event, context):
    """
    Main Lambda handler
    Triggered by S3:ObjectCreated events for CloudTrail logs
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        processed_count = 0
        failed_count = 0

        # Process each S3 record
        for record in event.get('Records', []):
            try:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']

                logger.info(f"Processing s3://{bucket}/{key}")

                # Download and decompress CloudTrail log
                logs = download_and_parse_logs(bucket, key)

                if logs:
                    # Send to CloudGuard backend in batches
                    count = send_logs_to_backend(logs)
                    processed_count += count
                    logger.info(f"Sent {count} logs to CloudGuard")
                else:
                    logger.warning(f"No logs found in {key}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing record: {str(e)}", exc_info=True)
                continue

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'CloudTrail logs processed',
                'processed': processed_count,
                'failed': failed_count
            })
        }

    except Exception as e:
        logger.error(f"Fatal error in Lambda handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def download_and_parse_logs(bucket, key):
    """
    Download CloudTrail log from S3 and decompress
    CloudTrail logs are gzipped JSON files
    """
    try:
        logger.info(f"Downloading s3://{bucket}/{key}")

        # Get object from S3
        response = s3.get_object(Bucket=bucket, Key=key)

        # Decompress gzip
        with gzip.GzipFile(fileobj=io.BytesIO(response['Body'].read())) as gzipfile:
            content = gzipfile.read().decode('utf-8')
            data = json.loads(content)

        logs = data.get('Records', [])
        logger.info(f"Parsed {len(logs)} events from CloudTrail log")

        return logs

    except Exception as e:
        logger.error(f"Error downloading/parsing logs: {str(e)}")
        raise


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

        try:
            logger.info(f"Sending batch {i//BATCH_SIZE + 1}: {len(batch)} logs")

            response = requests.post(
                CLOUDGUARD_API,
                json=payload,
                timeout=TIMEOUT,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                sent = result.get('count', len(batch))
                total_sent += sent
                logger.info(f"Successfully sent {sent} logs")
            else:
                logger.error(f"Backend returned status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending logs to backend: {str(e)}")
            # Continue with next batch instead of failing completely
            continue

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
