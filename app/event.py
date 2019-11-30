import os
from datetime import datetime

import pytz
from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, url_for)
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.orm.session import make_transient
from sqlalchemy.sql import func
from werkzeug.exceptions import NotFound

from . import mail
from .forms import EventEditForm, ConfirmDeleteEventForm
from .mail import send_single_mail
from .models import (Choices, Event, Group, GroupEventRelation, GroupMember,
                     Participant, User, db)
from .security import login_required, manager_required
from .utils import tz, url_back

bp = Blueprint("event", __name__, url_prefix="/event")

@bp.route('/')
def upcoming():
    pagination = Event.query.\
        order_by(Event.start.asc()).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
    return render_template('event/upcoming.html', pagination=pagination)


@bp.route('/<int:id>')
def view(id):
    event = Event.query.get_or_404(id)

    leaders = User.query.\
        join(GroupMember, GroupMember.user_id == User.id).\
        join(Group, Group.id == GroupMember.group_id).\
        join(GroupEventRelation, GroupEventRelation.group_id == Group.id).\
        join(Event, Event.id == GroupEventRelation.event_id).\
        filter(Event.id == id).\
        filter(GroupMember.role == GroupMember.Role.LEADER).\
        all()

    participants = Participant.query.options(joinedload(Participant.user)).\
        filter(Participant.event_id == event.id).\
        all()

    participants = []
    participant = None
    logged_in = g.user is not None

    for inv in participants:
        if inv.accepted_reply():
            participants.append(inv.user)
        if logged_in and inv.user_id == g.user.id:
            participant = inv

    return render_template(
        'event/event.html',
        event=event,
        leaders=leaders,
        participants=participants,
        participant=participant
    )


# @bp.route('/participants/<int:id>', methods=['GET'])
# @manager_required
# def participants(id):
#     event = Event.query.get_or_404(id)
#     pagination = None
#     stats = None

#     if event.invited:

#         stats = db.session.query(
#                 func.coalesce(func.sum(Participant.num_car_seats),0).label('car_seats'),
#                 func.coalesce(func.sum(Participant.num_friends),0).label('friends'),
#                 func.count(Participant.id).label('accepted')
#             ).\
#             filter(Participant.event_id == event.id).\
#             filter(Participant.reply == Participant.Reply.REGISTERED).\
#             first()

#         pagination = Participant.query.\
#             join(Participant.user).\
#             filter(Participant.event_id == id).\
#             filter_by_request(Participant.reply, 'filter.reply', Participant.Reply.get_values()).\
#             order_by_request(User.first_name, 'order.first_name').\
#             order_by_request(User.family_name, 'order.family_name').\
#             paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

#     return render_template(
#         'event/participants.html',
#         pagination=pagination,
#         stats=stats,
#         event=event,
#         args={**request.args.to_dict(), **{'id': event.id}},
#         ReplyChoices=Participant.Reply
#     )


# @bp.route('/invite/<int:id>', methods=['GET', 'POST'])
# @manager_required
# def invite(id):
#     event = Event.query.get_or_404(id)
#     now = tz.localize(datetime.now())

#     if event.deadline < now:
#         flash(f'Die Deadline zu Anmeldung von Anlass "{event.name}" ist vorbei, somit ist es sinnlos, noch Einladungen zu verschicken.', 'warning')
#         return redirect(url_for('event.edit', id=event.id))

#     if event.invited:
#         flash(f'Zum Anlass "{event.name}" wurden schon Einladungen versendet.', 'warning')
#         return redirect(url_for('participant.list', id=event.id))

#     users = User.query.\
#         join(GroupMember, GroupMember.user_id == User.id).\
#         join(Group, Group.id == GroupMember.group_id).\
#         join(GroupEventRelation, GroupEventRelation.group_id == Group.id).\
#         join(Event, Event.id == GroupEventRelation.event_id).\
#         filter(Event.id == id).\
#         order_by(User.username).\
#         all()

#     form = ConfirmForm()

#     if form.validate_on_submit():

#         participants = []
#         for user in users:
#             token = os.urandom(16).hex()
#             participants.append(Participant(user=user, event=event, token=token))
#         participant.list = participants
#         event.invited = True
#         db.session.commit()

#         for inv in participant.list:
#             token_url = url_for('participant.edit', id=inv.id, token=inv.token, _external=True)
#             send_single_mail(
#                 recipient=inv.user.email,
#                 subject=inv.event.name,
#                 text=render_template(
#                     'mail/participant.text',
#                     participant=inv, token_url=token_url),
#                 html=render_template(
#                     'mail/participant.html',
#                     participant=inv, token_url=token_url),
#             )

#     return render_template(
#         'event/invite.html',
#         users=users,
#         event=event,
#         form=form
#     )


# @bp.route('/update/<int:id>')
# @manager_required
# def update(id):
#     event = Event.query.get_or_404(id)
#     now = tz.localize(datetime.utcnow())

#     if event.deadline < now:
#         flash(f'Die Deadline zu Anmeldung von Anlass "{event.name}" ist vorbei, somit ist es sinnlos, noch Einladungen zu verschicken.', 'warning')
#         return redirect(url_for('event.edit', id=event.id))

#     form = ConfirmForm()

#     if form.validate_on_submit():
#         note = request.form.get('note')
#         for inv in participant.list:
#             token_url = url_for('participant.edit', id=inv.id, token=inv.token, _external=True)
#             send_single_mail(
#                 recipient=inv.user.email,
#                 subject=inv.event.name,
#                 text=render_template(
#                     'mail/update.text',
#                     participant=inv, token_url=token_url, note=note),
#                 html=render_template(
#                     'mail/udpate.html',
#                     participant=inv, token_url=token_url, note=note),
#             )

#     return render_template(
#         'event/update.html',
#         event=event,
#         form=form
#     )


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
        order_by_request(Event.deadline, 'order.deadline').\
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


@bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@manager_required
def delete(id):
    event = Event.query.get_or_404(id)
    form = ConfirmDeleteEventForm()

    if form.validate_on_submit():
        if 'confirm' in request.form:
            db.session.delete(event)
            db.session.commit()
            flash(f'{event.name} wurde gelöscht.', 'success')
        return redirect(url_for('event.list'))

    return render_template('event/delete.html', form=form, event=event)
