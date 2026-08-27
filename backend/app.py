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
from config           import Config
from database.database import init_db
from routes.api        import api

app = Flask(__name__)
CORS(app)  # Allow requests from React frontend on localhost:3000

# Register all routes under /api
app.register_blueprint(api, url_prefix="/api")

if __name__ == "__main__":
    init_db()
    print(f"\nCloudGuard backend running at http://localhost:{Config.PORT}")
    print("─" * 55)
    print("  GET  /api/stats")
    print("  GET  /api/logs")
    print("  GET  /api/logs/timeline/<1-5>")
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
    print("─" * 55 + "\n")
    app.run(debug=Config.DEBUG, port=Config.PORT)