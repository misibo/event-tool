import pytz
from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   url_for)
from sqlalchemy.orm import aliased

from .forms import AccountForm
from .models import Event, Group, GroupEventRelations, GroupMember, User, db
from .security import login_required

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route('/upcoming', methods=['GET', 'POST'])
@login_required
def upcoming():
    memberships = {m.group: m for m in g.user.memberships}
    pagination = Event.query.\
        join(Event.groups).\
        join(aliased(Group), aliased(GroupMember)).\
        join(User, GroupMember).\
        filter(User.id == g.user.id).\
        order_by(Event.start.asc()).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

    return render_template(
        'dashboard/upcoming.html',
        pagination=pagination,
        tz=pytz.timezone('Europe/Zurich'),
        memberships=memberships)

@bp.route('/memberships', methods=['GET', 'POST'])
@login_required
def memberships():
    pagination = GroupMember.query.\
        filter(GroupMember.user_id == g.user.id).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
    return render_template('dashboard/memberships.html', pagination=pagination)


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
