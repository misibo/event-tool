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
@auth.login_required
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
        return redirect(url_for('event.list'))

    return render_template('event/edit.html', form=form)


@bp.route('/<int:event_id>/participants', methods=['GET'])
@auth.login_required
def list_participants(event_id):
    event = db_session.query(Event).filter_by(id=event_id).first()
    if event is None:
        abort(NotFound)
    elif event.send_invitations:
        num_participants = 0
        num_car_seats = 0
        num_friends = 0

        order = {True: 0, False: 1, None: 2}

        invitations = event.invitations
        invitations = sorted(invitations, key=lambda x: (order[x.accepted], x.user.family_name, x.user.first_name))
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
    else:
        users = set()

        for group in event.groups:
            for user in group.users:
                users.add(user)

        users = sorted(users, key=lambda x: (x.family_name, x.first_name))

        return render_template(
            'event/list_audience.html', event=event, users=users)


@bp.route('/<int:event_id>/send_invitations', methods=['POST'])
@auth.login_required
def send_invitations(event_id):
    event = db_session.query(Event).filter_by(id=event_id).first()
    if event is None:
        abort(NotFound)
    else:
        event.send_invitations = True
        db_session.commit()

        from . import send_invitations
        send_invitations()
        return redirect(url_for('event.list_participants', event_id=event_id))


@bp.route('/<int:id>/delete', methods=['GET'])
@auth.login_required
def delete(id):
    event = db_session.query(Event).filter_by(id=id).first()
    if event is None:
        abort(NotFound)
    else:
        db_session.delete(event)
        db_session.commit()
        flash(f'Event "{event.name}" wurde erfolgreich gelöscht.')
        return redirect(url_for('event.list'))
