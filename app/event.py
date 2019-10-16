import os
from datetime import datetime

import pytz
from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from sqlalchemy.orm import aliased
from sqlalchemy.orm.session import make_transient
from werkzeug.exceptions import NotFound

from . import mailing
from .forms import EventEditForm
from .mailing import send_single_mail
from .models import (Choices, Event, Group, GroupEventRelations, GroupMember,
                     Invitation, User, db)
from .security import login_required, manager_required
from .utils import url_back

bp = Blueprint("event", __name__, url_prefix="/event")

tz = pytz.timezone('Europe/Zurich')

@bp.route('/')
def upcoming():
    pagination = Event.query.\
        order_by(Event.start.asc()).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
    return render_template('event/upcoming.html', pagination=pagination)


@bp.route('/<int:id>')
def view(id):
    event = Event.query.get_or_404(id)
    return render_template('event/event.html', event=event)


@bp.route('/invitations/<int:id>', methods=['GET'])
@manager_required
def invitations(id):
    event = Event.query.get_or_404(id)
    pagination = Invitation.query.\
        join(Invitation.user).\
        filter(Invitation.event_id == id).\
        filter_by_request(Invitation.reply, 'filter.reply', Invitation.Reply.get_values()).\
        order_by_request(User.first_name, 'order.first_name').\
        order_by_request(User.family_name, 'order.family_name').\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

    return render_template(
        'event/invitations.html',
        pagination=pagination,
        args={**request.args.to_dict(), **{'id': event.id}},
        ReplyChoices=Invitation.Reply,
        event=event
    )

# def list_participants(id):
#     event = Event.query.get_or_404(id)

#     if event.send_invitations:
#         num_participants = 0
#         num_car_seats = 0
#         num_friends = 0

#         order = {True: 0, False: 1, None: 2}

#         invitations = event.invitations
#         invitations = sorted(invitations, key=lambda x: (order[x.accepted], x.user.family_name, x.user.first_name))
#         for inv in invitations:
#             if inv.accepted:
#                 num_participants += 1
#                 if inv.num_car_seats is not None:
#                     num_car_seats += inv.num_car_seats
#                 if inv.num_friends is not None:
#                     num_friends += inv.num_friends

#         return render_template(
#             'event/list_participants.html', event=event, invitations=invitations,
#             num_participants=num_participants, num_car_seats=num_car_seats, num_friends=num_friends)
#     else:
#         users = set()

#         for group in event.groups:
#             for role in group.members:
#                 users.add(role.user)

#         users = sorted(users, key=lambda x: (x.family_name, x.first_name))

#         return render_template(
#             'event/list_audience.html', event=event, users=users)


@bp.route('/invite/<int:id>', methods=['GET', 'POST'])
@manager_required
def invite(id):
    event = Event.query.get_or_404(id)

    now = tz.localize(datetime.utcnow())

    if event.deadline < now:
        flash(f'Die Deadline zu Anmeldung von Anlass "{event.name}" ist vorbei, somit ist es sinnlos, noch Einladungen zu verschicken.', 'warning')
        return redirect(url_for('event.edit', id=event.id))

    if event.invitations:
        flash(f'Zum Anlass "{event.name}" wurden schon Einladungen versendet.', 'warning')
        return redirect(url_for('event.invitations', id=event.id))

    users = User.query.\
        join(GroupMember, GroupMember.user_id == User.id).\
        join(Group, Group.id == GroupMember.group_id).\
        join(GroupEventRelations, GroupEventRelations.group_id == Group.id).\
        join(Event, Event.id == GroupEventRelations.event_id).\
        filter(Event.id == id).\
        order_by(User.username).\
        all()

    if request.method == 'POST':

        invitations = []
        for user in users:
            token = os.urandom(16).hex()
            invitations.append(Invitation(user=user, event=event, token=token))
        event.invitations = invitations
        db.session.commit()

        for inv in event.invitations:
            token_url = request.url_root + url_for('invitation.mail_reply', id=inv.id, token=inv.token)[1:]
            send_single_mail(
                recipient=inv.user.email,
                subject=inv.event.name,
                text=render_template(
                    'mail/invitation.text',
                    invitation=inv, token_url=token_url),
                html=render_template(
                    'mail/invitation.html',
                    invitation=inv, token_url=token_url),
            )

    return render_template(
        'event/invite.html',
        users=users,
        event=event
    )


@bp.route('/update/<int:id>')
@manager_required
def update(id):
    event = Event.query.get_or_404(id)

    now = tz.localize(datetime.utcnow())

    if event.deadline < now:
        flash(f'Die Deadline zu Anmeldung von Anlass "{event.name}" ist vorbei, somit ist es sinnlos, noch Einladungen zu verschicken.', 'warning')
        return redirect(url_for('event.edit', id=event.id))

    if request.method == 'POST':
        note = request.form.get('note')
        for inv in event.invitations:
            token_url = request.url_root + url_for('invitation.mail_reply', id=inv.id, token=inv.token)[1:]
            send_single_mail(
                recipient=inv.user.email,
                subject=inv.event.name,
                text=render_template(
                    'mail/invitation.text',
                    invitation=inv, token_url=token_url, note=note),
                html=render_template(
                    'mail/invitation.html',
                    invitation=inv, token_url=token_url, note=note),
            )

    return render_template(
        'event/update.html',
        event=event
    )


class GroupChoices(Choices):

    def get_choices():
        return { g.id: g.name for g in Group.query.all() }

@bp.route('/list')
@manager_required
def list():
    pagination = Event.query.\
        order_by_request(Event.name, 'order.name').\
        order_by_request(Event.start, 'order.start').\
        order_by_request(Event.modified, 'order.modified').\
        filter_by_request(Group.id, 'filter.group', GroupChoices.get_values(), join=Event.groups).\
        order_by_request(Event.modified, 'order.deadline').\
        search_by_request([Event.name, Event.abstract, Event.details], 'search').\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

    return render_template(
        'event/list.html',
        pagination=pagination,
        args=request.args.to_dict(),
        GroupChoices=GroupChoices
    )


@bp.route('/create', methods=['GET', 'POST'])
@manager_required
def create():
    event = Event()
    form = EventEditForm(obj=event)

    if form.validate_on_submit():
        form.populate_obj(event)
        event.created = tz.localize(datetime.now())
        event.modified = tz.localize(datetime.now())
        db.session.add(event)
        db.session.commit()
        flash(f'Anlass "{event.name}" erstellt.', 'success')
        return redirect(url_back('event.list'))

    return render_template('event/edit.html', form=form, event=event)

@bp.route('/copy/<int:id>', methods=['GET'])
@manager_required
def copy(id):
    event = Event.query.get_or_404(id)
    name = event.name

    db.session.expunge(event)
    make_transient(event)

    event.id = None
    event.name =  f'{name} - Kopie'
    event.created = tz.localize(datetime.now())
    event.modified = tz.localize(datetime.now())

    db.session.add(event)
    db.session.commit()

    flash(f'Kopie von Anlass "{name}" erstellt.', 'success')
    return redirect(url_for('event.edit', id=event.id))

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@manager_required
def edit(id):
    event = Event.query.get_or_404(id)
    form = EventEditForm(obj=event)

    if form.validate_on_submit():
        form.populate_obj(event)
        event.modified = tz.localize(datetime.now())
        db.session.commit()
        flash(f'Anlass "{event.name}" gespeichert.', 'success')
        return redirect(url_back('event.list'))

    return render_template('event/edit.html', form=form, event=event)


@bp.route('/delete/<int:id>', methods=['GET'])
@manager_required
def delete(id):
    event = Event.query.get_or_404(id)
    flash(f'Anlass "{event.name}" gelöscht.', 'danger')
    db.session.delete(event)
    db.session.commit()
    return redirect(url_back('event.list'))
