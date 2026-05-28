from flask import Blueprint, render_template
from app.state import trigger_background_update

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    # Attempt a background update on page load (with a 30s cooldown)
    trigger_background_update(cooldown_seconds=30)
    return render_template('index.html')
