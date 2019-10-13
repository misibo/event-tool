from datetime import datetime

import pytz
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from sqlalchemy.orm import aliased
from .forms import EditInvitationForm
from .models import Event, Invitation, User, db, GroupMember, Group

bp = Blueprint("invitation", __name__, url_prefix="/invitation")


def list_missing_invitations():
    """Create model instances for missing invitations, but does not submit them to database.
    """
    import os
    # result = db.engine.execute("""
    # select User.id, Event.id
    # from User, Event, "Group"
    # inner join GroupMember
    #     on GroupMember.user_id = User.id and GroupMember.group_id = "Group".id
    # inner join GroupEventRelations
    #     on GroupEventRelations.event_id = Event.id and GroupEventRelations.group_id = "Group".id
    # left join Invitation
    #     on Invitation.user_id = User.id and Invitation.event_id == Event.id
    # where Event.send_invitations
    #     and Invitation.id is null
    #     and :utcnow <= Event.deadline
    # group by User.id, Event.id
    # """, dict(utcnow=datetime.utcnow()))

    Invitation2 = aliased(Invitation)
    result = db.session.query(User, Event) \
        .join(GroupMember.user) \
        .join(GroupMember.group) \
        .join(Group.events) \
        .join(Invitation, Invitation.user_id == User.id, isouter=True) \
        .join(Invitation2, Invitation2.event_id == Event.id, isouter=True) \
        .filter(Event.send_invitations) \
        .filter(Invitation.id == None) \
        .filter(pytz.utc.localize(datetime.utcnow()) <= Event.deadline) \
        .group_by(User.id, Event.id) \
        .all()

    invitations = []
    for user, event in result:
        token = os.urandom(16).hex()
        invitations.append(Invitation(user=user, event=event, token=token))
    return invitations


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    token = request.args.get('token', 'invalid')

    invitation = Invitation.query.filter_by(id=id).first()

    if invitation is None or invitation.token != token:
        flash('Die Einladung ist nicht gültig.', 'error')
        return redirect(url_for('index'))
    else:
        if pytz.utc.localize(datetime.utcnow()) > invitation.event.deadline:
            return render_template('invitation/invitation_post_deadline.html', invitation=invitation)
        else:
            form = EditInvitationForm(obj=invitation)

            if form.validate_on_submit():
                form.populate_obj(invitation)
                db.session.commit()

                if invitation.accepted:
                    flash(f'Du hast dich und {invitation.num_friends} weitere Freunde erfolgreich angemeldet.', 'info')
                    flash(f'{invitation.num_car_seats} Fahrplätze registriert.', 'info')
                else:
                    flash('Du hast dich erfolgreich abgemeldet.')

            return render_template(
                'invitation/invitation.html', form=form, invitation=invitation)
