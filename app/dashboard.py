from datetime import datetime

import pytz
from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   url_for)
from sqlalchemy.orm import aliased

from .forms import AccountForm
from .models import (Event, Group, GroupEventRelation, GroupMember,
                     Invitation, User, db)
from .security import login_required
from .utils import tz

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route('/upcoming', methods=['GET', 'POST'])
@login_required
def upcoming():
    pagination = Event.query.\
        join(GroupEventRelation, GroupEventRelation.event_id == Event.id).\
        join(Group, Group.id == GroupEventRelation.group_id).\
        join(GroupMember, GroupMember.group_id == Group.id).\
        filter(GroupMember.user_id == g.user.id).\
        filter(Event.start > tz.localize(datetime.now())).\
        order_by(Event.start.asc()).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

    invitations = Invitation.query.\
        join(Event, Event.id == Invitation.event_id).\
        filter(Invitation.user_id == g.user.id).\
        all()

    def find(items, attr, value):
        for item in items:
            if getattr(item, attr) == value:
                return item
        return None

    return render_template(
        'dashboard/upcoming.html',
        pagination=pagination,
        tz=tz,
        invitations=invitations,
        memberships=memberships,
        find=find
    )

@bp.route('/memberships', methods=['GET', 'POST'])
@login_required
def memberships():
    pagination = GroupMember.query.\
        filter(GroupMember.user_id == g.user.id).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

    return render_template(
        'dashboard/memberships.html',
        pagination=pagination
    )


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
