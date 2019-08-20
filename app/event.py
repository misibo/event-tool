from flask import Blueprint, abort, redirect, render_template, flash, url_for, session
from .models import Event, Group, db_session
from .forms import EventEditForm
from . import auth
from werkzeug.exceptions import NotFound
import pytz

bp = Blueprint("event", __name__, url_prefix="/events")


@bp.route('/', methods=['GET'])
@auth.login_required
def list():
    events = db_session.query(Event).all()
    return render_template('event/index.html', events=events, tz=pytz.timezone('Europe/Zurich'))


@bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    if id is None:
        event = Event()
    else:
        event = db_session.query(Event).filter_by(id=id).first()
        if event is None:
            abort(NotFound)

    form = EventEditForm(obj=event)
    form.groups.query = db_session.query(Group).all()

    if form.validate_on_submit():
        form.populate_obj(event)
        if id is None:
            db_session.add(event)
        db_session.commit()
        flash(f'Event "{event.name}" wurde erfolgreich gespeichert.')
        if event.send_invitations:
            from . import send_invitations
            send_invitations()
        return redirect(url_for('event.list'))

    return render_template('event/edit.html', form=form)


@bp.route('/<int:event_id>/list_participants', methods=['GET'])
@auth.login_required
def list_participants(event_id):
    event = db_session.query(Event).filter_by(id=event_id).first()
    if event is None:
        abort(NotFound)
    else:
        num_participants = 0
        num_car_seats = 0
        num_friends = 0

        invitations = event.invitations
        for inv in invitations:
            if inv.accepted:
                num_participants += 1
                if inv.num_car_seats is not None:
                    num_car_seats += inv.num_car_seats
                if inv.num_friends is not None:
                    num_friends += inv.num_friends

        return render_template(
            'event/list_participants.html', event=event, invitations=invitations,
            num_participants=num_participants, num_car_seats=num_car_seats, num_friends=num_friends)


@bp.route('/<int:id>/delete', methods=['GET'])
def delete(id):
    event = db_session.query(Event).filter_by(id=id).first()
    if event is None:
        abort(NotFound)
    else:
        db_session.delete(event)
        db_session.commit()
        flash(f'Event "{event.name}" wurde erfolgreich gelöscht.')
        return redirect(url_for('event.list'))
