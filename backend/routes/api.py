from flask import Blueprint
from routes.logs    import logs_bp
from routes.alerts  import alerts_bp
from routes.stats   import stats_bp
from routes.prowler import prowler_bp

api = Blueprint("api", __name__)
api.register_blueprint(logs_bp)
api.register_blueprint(alerts_bp)
api.register_blueprint(stats_bp)
api.register_blueprint(prowler_bp)