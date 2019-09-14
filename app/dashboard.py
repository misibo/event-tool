from flask import Blueprint, flash, g, render_template, redirect, url_for

from .forms import AccountForm
from .models import User, db
from .security import login_required

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    user: User = g.user
    return render_template('user/index.html', user=user)


@bp.route('/index', methods=['GET', 'POST'])
def index():
    return redirect(url_for('dashboard.account'))


@bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user: User = g.user
    form = AccountForm(obj=user)

    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()

        flash('Profil erfolgreich angepasst.')

    return render_template('dashboard/account.html', form=form)
