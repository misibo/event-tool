from datetime import datetime

import pytz
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from sqlalchemy.orm import aliased
from .forms import EditInvitationForm
from .models import Event, Invitation, User, db, GroupMember, Group
from .security import manager_required

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

@bp.route('/decline/<int:id>', methods=['GET', 'POST'])
def decline(id):
    invitation = Invitation.query.get_or_404()
    if invitation.user_id != g.user.id and g.user.role != User.Role.MANAGER:
        return flask.abort(403)

    invitation.reply = Invitation.Reply.DECLINED
    db.session.commit()

    flash('Du hast die Einladung abgelehnt.')

    return redirect(request.args.get('redirect_url'))

@bp.route('/accept/<int:id>', methods=['GET', 'POST'])
def accept(id):
    invitation = Invitation.query.get_or_404()
    if invitation.user_id != g.user.id and g.user.role != User.Role.MANAGER:
        return flask.abort(403)

    invitation.accepted = Invitation.Reply.ACCEPTED
    db.session.commit()

    flash('Du hast die Einladung angenommen.')

    return redirect(request.args.get('redirect_url'))

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@manager_required
def edit(id):
    invitation = Invitation.query.get_or_404(id)

    form = EditInvitationForm(obj=invitation)

    if form.validate_on_submit():
        form.populate_obj(invitation)
        db.session.commit()

        return redirect(url_for('event.invitations', id=invitation.event.id))

    return render_template(
        'invitation/edit.html',
        form=form,
        invitation=invitation
    )


@bp.route('/mail_reply/<int:id>', methods=['GET', 'POST'])
def mail_reply(id):
    token = request.args.get('token', 'invalid')

    invitation = Invitation.query.get_or_404(id)

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

                if invitation.reply == Invitation.Reply.ACCEPTED:
                    flash(f'Du hast dich und {invitation.num_friends} weitere Freunde erfolgreich angemeldet.', 'info')
                    flash(f'{invitation.num_car_seats} Fahrplätze registriert.', 'info')
                elif Invitation.Reply.DECLINED:
                    flash('Du hast dich erfolgreich abgemeldet.')

                return redirect(url_for('event.view', id=invitation.event.id))

            return render_template(
                'invitation/edit.html',
                form=form,
                invitation=invitation
            )
