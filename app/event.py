from flask import Blueprint, abort, redirect, render_template, flash, url_for, session
from .models import Event, Group, db_session
from .forms import EventEditForm
from . import auth
from werkzeug.exceptions import NotFound
import pytz

bp = Blueprint("event", __name__, url_prefix="/event")


@bp.route('/', methods=['GET'])
@auth.login_required
def list():
    events = db_session.query(Event).all()
    return render_template('event/index.html', events=events, tz=pytz.timezone('Europe/Zurich'))


@bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
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


@bp.route('/delete/<int:id>', methods=['GET'])
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
