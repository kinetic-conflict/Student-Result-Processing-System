from flask import Blueprint, render_template, request

from services import audit
from services.pagination import paginate

audit_view_bp = Blueprint('audit_view', __name__, url_prefix='/admin/audit')


@audit_view_bp.route('')
def entries():
    """The audit log, newest first."""
    search = request.args.get('search', '').strip()
    page = paginate(audit.count(search or None), request.args.get('page'))
    return render_template('audit.html', entries=audit.recent(page.per_page, page.offset, search or None),
                           page=page, search=search)
