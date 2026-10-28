from flask import Blueprint, g, redirect

import security

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Send each signed-in user to their own home page."""
    return redirect(security.home_url(g.user))
