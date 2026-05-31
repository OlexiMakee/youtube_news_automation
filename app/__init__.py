import os
from flask import Flask


def create_app():
    # Calculate root directory relative to this file
    app_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(app_dir)
    
    app = Flask(__name__,
                template_folder=os.path.join(root_dir, "templates"),
                static_folder=os.path.join(root_dir, "static"))
    
    # Import and register blueprints
    from app.routes.main import main_bp
    from app.routes.stats import stats_bp
    from app.routes.videos import videos_bp
    from app.routes.charts import charts_bp
    from app.routes.actions import actions_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(actions_bp)
    
    # Initialize v1.1.0 SaaS infrastructure (Phase 2)
    _init_telemetry_and_rotation(root_dir)
    
    return app


def _init_telemetry_and_rotation(root_dir):
    """Initialize telemetry daemon and cloud rotation engine (v1.1.0)."""
    try:
        db_path = os.path.join(root_dir, "data", "youtube_news.db")
        
        # Start telemetry daemon (collects system metrics)
        from app.services.telemetry import start_telemetry
        start_telemetry(db_path, interval=10)
        
        # Initialize cloud rotation engine (LLM provider switching)
        from app.services.cloud_rotation import init_rotation_engine
        init_rotation_engine(db_path)
        
        print("[App Init] ✅ Telemetry daemon started")
        print("[App Init] ✅ Cloud rotation engine initialized")
    
    except Exception as e:
        print(f"[App Init] ⚠️  SaaS infrastructure initialization warning: {e}")
        # Non-blocking: if telemetry fails, app continues
