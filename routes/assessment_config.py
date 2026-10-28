from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from routes.helpers import client_ip
from services import assessment_config, audit
from services.validation import ValidationError, parse_decimal

assessment_config_bp = Blueprint('assessment_config', __name__, url_prefix='/admin/assessment-config')


@assessment_config_bp.route('', methods=['GET', 'POST'])
def settings():
    """Edit each component's maximum marks and weight. Applies to every result at once."""
    config = assessment_config.load_config()
    typed = {}
    if request.method == 'POST':
        try:
            values = {}
            for item in config:
                keys = (f"max_{item['assessment_id']}", f"weight_{item['assessment_id']}")
                typed.update({key: request.form.get(key, '') for key in keys})
                values[item['assessment_id']] = (
                    parse_decimal(f"Maximum marks for {item['code']}", typed[keys[0]], places=2),
                    parse_decimal(f"Weight for {item['code']}", typed[keys[1]], places=2))
            changes = assessment_config.update_config(values)
        except ValidationError as error:
            flash(str(error), 'error')
        else:
            if changes:
                audit.record(g.user, 'assessment_config.update', 'assessments', None,
                             '; '.join(changes), client_ip())
            flash('Assessment settings saved.' if changes else 'No changes to save.', 'success')
            return redirect(url_for('assessment_config.settings'))
    return render_template('assessment_config.html', config=config, typed=typed)
