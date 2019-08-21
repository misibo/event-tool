from flask import Blueprint, render_template, flash, g
from .forms import EditUserForm
from .security import login_required
from .models import User, db

bp = Blueprint("user", __name__, url_prefix="/user")

@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    user: User = g.user
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.first_name = form.first_name.data
        user.family_name = form.family_name.data
        db.session.commit()

        flash('Profil erfolgreich angepasst.')

    return render_template('user/edit.html', form=form)
