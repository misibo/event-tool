import os
from datetime import datetime

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
from .utils import url_back, now

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
        event.created = now
        event.modified = now
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
    event.created = now
    event.modified = now

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
        event.modified = now
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
