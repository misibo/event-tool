from datetime import datetime
import os
import pytz
from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, url_for)
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import func

from .forms import EditParticipantForm
from .models import Event, Group, GroupMember, Participant, User, db
from .security import manager_required, login_required
from .utils import tz, url_back, now

bp = Blueprint("participant", __name__, url_prefix="/event")

@bp.route('/<int:id>/participant/list', methods=['GET'])
@manager_required
def list(id):
    event = Event.query.get_or_404(id)
    stats = None

    if event.registration_start and event.registration_start < now:
        stats = db.session.query(
                func.coalesce(func.sum(Participant.num_car_seats),0).label('car_seats'),
                func.coalesce(func.sum(Participant.num_friends),0).label('friends'),
                func.count(Participant.id).label('accepted')
            ).\
            filter(Participant.event_id == event.id).\
            filter(Participant.registration_status == Participant.RegistrationStatus.REGISTERED).\
            first()

    pagination = Participant.query.\
        join(Participant.user).\
        filter(Participant.event_id == id).\
        filter_by_request(Participant.registration_status, 'filter.reply', Participant.RegistrationStatus.get_values()).\
        order_by_request(User.first_name, 'order.first_name').\
        order_by_request(User.family_name, 'order.family_name').\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])

    return render_template(
        'participant/list.html',
        pagination=pagination,
        stats=stats,
        event=event,
        args={**request.args.to_dict(), **{'id': event.id}},
        RegistrationStatusChoices=Participant.RegistrationStatus
    )

@bp.route('/<int:id>/participate', methods=['GET', 'POST'])
@login_required
def participate(id):
    event = Event.query.get_or_404(id)
    form = EditParticipantForm()
    participant = Participant(
        event=event
    )

    if form.validate_on_submit():
        participant.user = g.user
        participant.token = os.urandom(16).hex()
        form.populate_obj(participant)
        db.session.add(participant)
        db.session.commit()

        flash(f'Deine Teilnahmestatus für den Anlass "{event.name}" ist: "{participant.get_registration_status_label()}"')
        if participant.is_registered():
            flash(f'Du hast {participant.num_friends} Freunde angemeldet und {participant.num_car_seats} Fahrplätze angeboten.')
        return redirect(url_for('event.view', id=event.id))

    form.registration_status.data = Participant.RegistrationStatus.REGISTERED
    del(form.registration_status.choices[0])

    return render_template(
        'participant/edit.html',
        form=form,
        participant=participant,
        editing=False
    )

@bp.route('/participant/<string:token>/edit', methods=['GET', 'POST'])
@bp.route('/participant/<int:id>/edit', methods=['GET', 'POST'])
def edit(id=0, token=''):
    editing = False
    query = Participant.query.\
        options(joinedload(Participant.user), joinedload(Participant.event))

    if token:
        participant = query.\
            filter(Participant.token == token).\
            first_or_404()
    elif id:
        if g.user is None:
            return redirect(url_for('security.login', redirect_url=request.url))
        participant = query.get_or_404(id)
        editing = participant.user_id != g.user.id
    else:
        return abort(404)

    if editing and not g.user.can_manage():
        return flask.abort(403)

    if participant.event.deadline < now:
        flash(f'Die Deadline, um auf die Einladung für Anlass "{participant.event.name}" ist vorüber!')
        return redirect(url_back(url_for('participant.list')) if editing else url_back(url_for('event.view', id=participant.event.id)))

    form = EditParticipantForm(obj=participant)

    if form.validate_on_submit():
        form.populate_obj(participant)
        db.session.commit()

        if editing:
            flash(f'"{participant.user.get_fullname()}" ist nun für den Anlass "{participant.event.name}" {participant.get_registration_status_label()}')
        else:
            flash(f'Deine Anwort auf die Einladung für den Anlass "{participant.event.name}" ist: "{participant.get_registration_status_label()}"')

        if participant.is_registered():
            flash(f'Du hast {participant.num_friends} Freunde angemeldet und {participant.num_car_seats} Fahrplätze registriert.')
        return redirect(url_for('participant.list', id=participant.event.id))

    return render_template(
        'participant/edit.html',
        form=form,
        participant=participant,
        editing=editing
    )
