from flask import Blueprint, abort, redirect, render_template, flash, url_for
from .models import Event, Group, db_session
from .forms import EventEditForm
from werkzeug.exceptions import NotFound

bp = Blueprint("event", __name__, url_prefix="/event")


@bp.route('/', methods=['GET'])
def list():
    events = db_session.query(Group).all()
    return render_template('index.html', events=groups)


@bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if id is None:
        event = Event()
    else:
        event = db_session.query(Event).filter_by(id=id).first()
        if event is None:
            abort(NotFound)

    form = EventEditForm(obj=event)
    form.groups.choices = []
    for group in db_session.query(Group).all():
        form.groups.choices.append( (group.id, group.name) )

    if form.validate_on_submit():
        form.populate_obj(event)
        if id is None:
            db_session.add(event)
        db_session.commit()
        flash(f'Event "{event.title}" wurde erfolgreich gespeichert.')
        return redirect(url_for('event.list'))

    return render_template('event/edit.html', form=form)


@bp.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    event = db_session.query(Event).filter_by(id=id).first()
    if event is None:
        abort(NotFound)
    else:
        db_session.delete(event)
        db_session.commit()
        flash(f'Event "{event.title}" wurde erfolgreich gelöscht.')
        return redirect(url_for('event.list'))
