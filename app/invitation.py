from datetime import datetime

import pytz
from flask import Blueprint, flash, redirect, render_template, request, url_for

from .forms import EditInvitationForm
from .models import Event, Invitation, User, db

bp = Blueprint("invitation", __name__, url_prefix="/invitation")


def list_missing_invitations():
    """Create model instances for missing invitations, but does not submit them to database.
    """
    import os
    result = db.engine.execute("""
        with MissingInvitations as (
            with EligibleInvitations as (
                select distinct
                    GroupEventRelations.event_id as event_id,
                    GroupMember.user_id
                from GroupEventRelations
                inner join GroupMember on GroupMember.group_id = GroupEventRelations.group_id
            )
            select event_id, user_id from EligibleInvitations
            except
            select event_id, user_id from Invitation
        )
        select User.id as user_id, Event.id as event_id from MissingInvitations
        inner join User on User.id = MissingInvitations.user_id
        inner join Event on Event.id = MissingInvitations.event_id
        where Event.send_invitations = True
            and :utcnow <= Event.deadline
        order by User.id, Event.id
        """, dict(utcnow=datetime.utcnow()))

    invitations = []
    for user_id, event_id in result:
        token = os.urandom(16).hex()
        user = User.query.filter_by(id=user_id).first()
        event = Event.query.filter_by(id=event_id).first()
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
