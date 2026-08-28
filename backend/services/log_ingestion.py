"""
backend/services/log_ingestion.py
Handles real-time log ingestion and processing from Lambda
"""

import json
import logging
from datetime import datetime, timedelta
from database.database import get_db
from services.detection import detect_threat_from_log
from routes.live_logs import broadcast_new_logs, broadcast_new_alert

logger = logging.getLogger(__name__)


class LogIngestionService:
    """Service for ingesting and processing logs in real-time"""

    @staticmethod
    def ingest_logs(logs, source='cloudtrail'):
        """
        Ingest a batch of logs

        Args:
            logs: List of log entries
            source: Source of logs (cloudtrail, vpc_flow_logs, cloudwatch, etc.)

        Returns:
            Dict with ingestion stats
        """
        stats = {
            'total': len(logs),
            'processed': 0,
            'alerts': 0,
            'errors': 0
        }

        processed_logs = []

        for log_entry in logs:
            try:
                # Parse log entry
                log_record = parse_log(log_entry, source)
                logger.info(f"Parsed log: {log_record.get('event')}")

                # Run threat detection
                severity, reasons = detect_threat_from_log(log_record)
                logger.info(f"Threat detection: severity={severity}, reasons={reasons}")

                # Create alert if threat detected
                if severity:
                    alert = create_alert(log_record, severity, reasons)
                    broadcast_new_alert(alert)
                    stats['alerts'] += 1
                    logger.info(f"Alert created: {alert['title']}")

                # Save log to database
                log_id = save_log(log_record)
                logger.info(f"Log saved with ID: {log_id}")
                if log_id:
                    log_record['id'] = log_id
                    processed_logs.append(log_record)
                    stats['processed'] += 1

            except Exception as e:
                logger.error(f"Error processing log: {str(e)}", exc_info=True)
                stats['errors'] += 1
                continue

        # Broadcast new logs to WebSocket clients
        if processed_logs:
            broadcast_new_logs(processed_logs)

        logger.info(f"Ingestion complete: {stats}")
        return stats


def parse_log(log_entry, source):
    """Parse log entry based on source format"""

    if source == 'cloudtrail':
        return parse_cloudtrail_log(log_entry)
    elif source == 'vpc_flow_logs':
        return parse_vpc_flow_log(log_entry)
    elif source == 'cloudwatch':
        return parse_cloudwatch_log(log_entry)
    else:
        return parse_generic_log(log_entry)


def parse_cloudtrail_log(entry):
    """Parse CloudTrail log entry (handles both full and simplified formats)"""
    user_identity = entry.get('userIdentity', {})
    request_params = entry.get('requestParameters', {})

    return {
        'timestamp': entry.get('eventTime') or entry.get('timestamp'),
        'user': user_identity.get('userName') or entry.get('user', 'unknown'),
        'user_type': user_identity.get('type', 'unknown'),
        'principal_id': user_identity.get('principalId'),
        'event': entry.get('eventName') or entry.get('event'),
        'source': entry.get('eventSource') or entry.get('source'),
        'ip': entry.get('sourceIPAddress') or entry.get('ip'),
        'region': entry.get('awsRegion') or entry.get('region'),
        'user_agent': entry.get('userAgent'),
        'status': 'success' if entry.get('errorCode') is None else 'error',
        'error_code': entry.get('errorCode'),
        'error_message': entry.get('errorMessage'),
        'resource': request_params.get('bucketName') or entry.get('resource') or 'unknown',
        'raw': json.dumps(entry),
        'source_type': 'cloudtrail'
    }


def parse_vpc_flow_log(entry):
    """Parse VPC Flow Log entry"""
    return {
        'timestamp': entry.get('end'),
        'source_ip': entry.get('srcaddr'),
        'destination_ip': entry.get('dstaddr'),
        'source_port': entry.get('srcport'),
        'destination_port': entry.get('dstport'),
        'protocol': entry.get('protocol'),
        'packets': entry.get('packets'),
        'bytes': entry.get('bytes'),
        'action': entry.get('action'),
        'raw': json.dumps(entry),
        'source_type': 'vpc_flow_logs'
    }


def parse_cloudwatch_log(entry):
    """Parse CloudWatch log entry"""
    return {
        'timestamp': entry.get('@timestamp'),
        'message': entry.get('@message'),
        'log_stream': entry.get('@logStream'),
        'raw': json.dumps(entry),
        'source_type': 'cloudwatch'
    }


def parse_generic_log(entry):
    """Parse generic log entry"""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'raw': json.dumps(entry),
        'source_type': 'generic'
    }


def save_log(log_record):
    """Save log to database"""
    from database.database import get_db

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO logs (
                timestamp, user, event, source, ip, region,
                user_agent, status, error_code, resource, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_record.get('timestamp'),
            log_record.get('user'),
            log_record.get('event'),
            log_record.get('source'),
            log_record.get('ip'),
            log_record.get('region'),
            log_record.get('user_agent'),
            log_record.get('status'),
            log_record.get('error_code'),
            log_record.get('resource'),
            log_record.get('raw')
        ))

        conn.commit()
        log_id = cursor.lastrowid
        logger.info(f"Log saved to database with ID: {log_id}")
        return log_id
    except Exception as e:
        logger.error(f"Error saving log: {str(e)}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()


def create_alert(log_record, severity, reasons):
    """Create alert for suspicious activity"""
    from database.database import get_db

    alert = {
        'title': f"{severity} severity event: {log_record.get('event')}",
        'description': ' | '.join(reasons),
        'severity': severity,
        'user': log_record.get('user'),
        'event': log_record.get('event'),
        'source': log_record.get('source'),
        'ip': log_record.get('ip'),
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'Open',
        'related_log_id': None
    }

    # Save to database
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO alerts (
            title, description, severity, user, event, source,
            ip, timestamp, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        alert['title'],
        alert['description'],
        alert['severity'],
        alert['user'],
        alert['event'],
        alert['source'],
        alert['ip'],
        alert['timestamp'],
        alert['status']
    ))

    conn.commit()
    alert['id'] = cursor.lastrowid

    return alert
