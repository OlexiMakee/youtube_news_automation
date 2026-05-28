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
    
    return app
