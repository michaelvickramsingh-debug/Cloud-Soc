"""
app.py
------
CloudGuard backend entry point.

Run with:
    cd backend
    python app.py

What happens on startup:
  1. Load .env via config.py
  2. Initialise the SQLite database (creates tables + seeds scenarios)
  3. Register all API blueprints under /api
  4. Start Flask dev server on port 5000
"""

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from config           import Config
from database.database import init_db
from routes.api        import api
from routes.live_logs  import live_logs_bp, init_socketio

app = Flask(__name__)
CORS(app)  # Allow requests from React frontend on localhost:3000

# Initialize WebSocket support for real-time log streaming
socketio = SocketIO(app, cors_allowed_origins="*")
init_socketio(socketio)

# Register all routes under /api
app.register_blueprint(api, url_prefix="/api")
app.register_blueprint(live_logs_bp, url_prefix="/api")

if __name__ == "__main__":
    init_db()
    print(f"\nCloudGuard backend running at http://localhost:{Config.PORT}")
    print("─" * 55)
    print("  GET  /api/stats")
    print("  GET  /api/logs")
    print("  GET  /api/logs/timeline/<1-5>")
    print("  POST /api/logs/ingest (Lambda)")
    print("  GET  /api/alerts")
    print("  GET  /api/alerts/summary")
    print("  PUT  /api/alerts/<id>/resolve")
    print("  GET  /api/scenarios")
    print("  POST /api/simulate/<1-5>")
    print("  GET  /api/metrics")
    print("  GET  /api/mitre")
    print("  POST /api/reset")
    print("  POST /api/prowler/ingest")
    print("  GET  /api/prowler/summary")
    print("─" * 55)
    print("  WebSocket: ws://localhost:5001/logs")
    print("─" * 55 + "\n")
    socketio.run(app, debug=Config.DEBUG, port=Config.PORT, host="0.0.0.0")