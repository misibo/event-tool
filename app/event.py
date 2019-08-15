from flask import Blueprint, abort, redirect, render_template, flash, url_for
from .models import Event, Group, db
from .forms import EventEditForm
from werkzeug.exceptions import NotFound

bp = Blueprint("event", __name__, url_prefix="/event")


@bp.route('/', methods=['GET'])
def list():
    events = Event.query.all()
    return render_template('event/index.html', events=events)


@bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if id is None:
        event = Event()
    else:
        event = Event.query.filter_by(id=id).first()
        if event is None:
            abort(NotFound)

    form = EventEditForm(obj=event)
    form.groups.query = Group.query.all()

    if form.validate_on_submit():
        form.populate_obj(event)
        if id is None:
            db.session.add(event)
        db.session.commit()
        flash(f'Event "{event.name}" wurde erfolgreich gespeichert.')
        return redirect(url_for('event.list'))

    return render_template('event/edit.html', form=form)


@bp.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    event = Event.query.filter_by(id=id).first()
    if event is None:
        abort(NotFound)
    else:
        db.session.delete(event)
        db.session.commit()
        flash(f'Event "{event.name}" wurde erfolgreich gelöscht.')
        return redirect(url_for('event.list'))
