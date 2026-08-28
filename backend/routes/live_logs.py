"""
backend/routes/live_logs.py
Real-time log ingestion and WebSocket streaming
"""

from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, leave_room
import logging
import json

logger = logging.getLogger(__name__)

live_logs_bp = Blueprint('live_logs', __name__)
socketio = None  # Initialized in app.py


def init_socketio(socket_instance):
    """Initialize socketio for this module"""
    global socketio
    socketio = socket_instance

    # Register WebSocket event handlers after socketio is initialized
    @socketio.on('connect', namespace='/logs')
    def handle_connect():
        """Handle WebSocket connection"""
        logger.info(f'Client connected to /logs: {request.sid}')
        emit('connected', {'message': 'Connected to log stream'})

    @socketio.on('disconnect', namespace='/logs')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        logger.info(f'Client disconnected from /logs: {request.sid}')

    @socketio.on('subscribe', namespace='/logs')
    def handle_subscribe(data):
        """
        Subscribe to log stream with optional filters

        Data format:
        {
            "filters": {
                "severity": "High",      # Optional
                "source": "s3",          # Optional
                "event": "GetObject",    # Optional
                "user": "alice"          # Optional
            }
        }
        """
        try:
            filters = data.get('filters', {}) if data else {}
            join_room(f"logs_stream_{request.sid}")

            emit('subscribed', {
                'status': 'subscribed',
                'filters': filters,
                'message': 'Now receiving live logs'
            })

            logger.info(f'Client {request.sid} subscribed with filters: {filters}')

        except Exception as e:
            logger.error(f"Error handling subscribe: {str(e)}")
            emit('error', {'message': str(e)})

    @socketio.on('unsubscribe', namespace='/logs')
    def handle_unsubscribe():
        """Unsubscribe from log stream"""
        leave_room(f"logs_stream_{request.sid}")
        emit('unsubscribed', {'status': 'unsubscribed'})

    @socketio.on('filter_update', namespace='/logs')
    def handle_filter_update(data):
        """Update filters for log stream"""
        try:
            filters = data.get('filters', {})
            logger.info(f'Client {request.sid} updated filters: {filters}')
            emit('filter_updated', {'filters': filters})

        except Exception as e:
            logger.error(f"Error updating filters: {str(e)}")
            emit('error', {'message': str(e)})


# ================== REST Endpoints ==================

@live_logs_bp.route('/logs/ingest', methods=['POST'])
def ingest_logs():
    """
    Endpoint for Lambda to send parsed CloudTrail logs

    Expected payload:
    {
        "logs": [...],           # Array of parsed log entries
        "source": "cloudtrail",  # Source of logs
        "timestamp": "2024-08-27T10:15:30Z"
    }
    """
    try:
        # Import here to avoid circular imports
        from services.log_ingestion import LogIngestionService

        data = request.get_json()

        if not data or 'logs' not in data:
            return jsonify({'error': 'Missing logs in request'}), 400

        logs = data.get('logs', [])
        source = data.get('source', 'unknown')

        # Process logs
        stats = LogIngestionService.ingest_logs(logs, source)

        # Broadcast to connected WebSocket clients
        if socketio:
            socketio.emit('ingestion_complete', stats, to=None, namespace='/logs')

        return jsonify({
            'status': 'ok',
            'count': stats['processed'],
            'alerts': stats['alerts']
        }), 200

    except Exception as e:
        logger.error(f"Error ingesting logs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@live_logs_bp.route('/logs/stream/status', methods=['GET'])
def stream_status():
    """Get current streaming status"""
    return jsonify({
        'status': 'connected',
        'websocket_url': 'ws://localhost:5001/logs'
    }), 200


def broadcast_new_logs(logs):
    """
    Broadcast new logs to all connected WebSocket clients
    Called by log ingestion service
    """
    if socketio and logs:
        import datetime
        socketio.emit('new_logs', {
            'logs': logs,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }, namespace='/logs', skip_sid=None)
        logger.info(f"Broadcasted {len(logs)} logs to WebSocket clients")


def broadcast_new_alert(alert):
    """
    Broadcast new alert to all connected WebSocket clients
    Called when threat is detected
    """
    if socketio and alert:
        socketio.emit('new_alert', alert, namespace='/logs', skip_sid=None)
        logger.info(f"Broadcasted alert: {alert.get('title', 'Unknown')}")
