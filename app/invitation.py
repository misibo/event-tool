from datetime import datetime

import pytz
from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, url_for)
from sqlalchemy.orm import aliased, joinedload

from .forms import EditInvitationForm
from .models import Event, Group, GroupMember, Invitation, User, db
from .security import manager_required
from .utils import tz, url_back

bp = Blueprint("invitation", __name__, url_prefix="/invitation")


# def list_missing_invitations():
#     """Create model instances for missing invitations, but does not submit them to database.
#     """
#     import os
#     # result = db.engine.execute("""
#     # select User.id, Event.id
#     # from User, Event, "Group"
#     # inner join GroupMember
#     #     on GroupMember.user_id = User.id and GroupMember.group_id = "Group".id
#     # inner join GroupEventRelations
#     #     on GroupEventRelations.event_id = Event.id and GroupEventRelations.group_id = "Group".id
#     # left join Invitation
#     #     on Invitation.user_id = User.id and Invitation.event_id == Event.id
#     # where Event.send_invitations
#     #     and Invitation.id is null
#     #     and :utcnow <= Event.deadline
#     # group by User.id, Event.id
#     # """, dict(utcnow=datetime.utcnow()))

#     Invitation2 = aliased(Invitation)
#     result = db.session.query(User, Event) \
#         .join(GroupMember.user) \
#         .join(GroupMember.group) \
#         .join(Group.events) \
#         .join(Invitation, Invitation.user_id == User.id, isouter=True) \
#         .join(Invitation2, Invitation2.event_id == Event.id, isouter=True) \
#         .filter(Event.send_invitations) \
#         .filter(Invitation.id == None) \
#         .filter(pytz.utc.localize(datetime.utcnow()) <= Event.deadline) \
#         .group_by(User.id, Event.id) \
#         .all()

#     invitations = []
#     for user, event in result:
#         token = os.urandom(16).hex()
#         invitations.append(Invitation(user=user, event=event, token=token))
#     return invitations


@bp.route('/edit/<string:token>', methods=['GET', 'POST'])
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id=0, token=''):
    editing = False
    query = Invitation.query.options(joinedload(Invitation.user), joinedload(Invitation.event))
    if token:
        invitation = query.\
            filter(Invitation.token == token).\
            first_or_404()
    elif id:
        if g.user is None:
            return redirect(url_for('security.login', redirect_url=request.url))
        invitation = query.get_or_404(id)
        editing = invitation.user_id != g.user.id
    else:
        return abort(404)

    if editing and not g.user.can_manage():
        return flask.abort(403)

    if invitation.event.deadline < tz.localize(datetime.now()):
        flash('Die Deadline, um auf die Einladung für Anlass "{invitation.event.name}" ist vorüber!')
        return redirect(url_back('event.invitations') if editing else url_back('event.view', id=invitation.event.id))

    form = EditInvitationForm(obj=invitation)

    if form.validate_on_submit():
        form.populate_obj(invitation)
        db.session.commit()

        if editing:
            flash(f'Die Antwort von "{invitation.user.get_fullname()}" auf die Einladung für Anlass "{invitation.event.name}" ist "{invitation.get_reply_label()}"')
        else:
            flash(f'Deine Anwort auf die Einladung für den Anlass "{invitation.event.name}" ist: "{invitation.get_reply_label()}"')

        if invitation.accepted_reply():
            flash(f'Es sind {invitation.num_friends} Freunde angemeldet und {invitation.num_car_seats} Fahrplätze registriert worden.')
        return redirect(url_for('event.invitations', id=invitation.event.id))

    return render_template(
        'invitation/edit.html',
        form=form,
        invitation=invitation,
        editing=editing
    )
