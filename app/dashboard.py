from flask import Blueprint, flash, g, render_template

from .forms import EditUserForm
from .models import User, db
from .security import login_required

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    user: User = g.user
    return render_template('user/index.html', user=user)


@bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user: User = g.user
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.first_name = form.first_name.data
        user.family_name = form.family_name.data
        db.session.commit()

        flash('Profil erfolgreich angepasst.')

    return render_template('user/account.html', form=form)
