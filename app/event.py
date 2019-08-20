from flask import Blueprint
from .models import Event
from .forms import EventEditForm
from .views import ListView, CreateEditView, DeleteView

bp = Blueprint("event", __name__, url_prefix="/event")


class EventListView(ListView):
    sorts = ['name', 'start', 'deadline', 'modified']
    searchable = ['name', 'description', 'location', 'equipment']
    model = Event
    template = 'event/index.html'


class EventCreateEditView(CreateEditView):

    form = EventEditForm
    model = Event
    template = 'event/edit.html'
    redirect = 'event.list'


class EventDeleteView(DeleteView):
    model = Event
    redirect = 'event.list'


bp.add_url_rule(
    '/',
    view_func=EventListView.as_view('list'),
    methods=['GET']
)
bp.add_url_rule(
    '/create',
    defaults={'id': None},
    view_func=EventCreateEditView.as_view('create'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/edit/<int:id>',
    view_func=EventCreateEditView.as_view('edit'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/delete/<int:id>',
    view_func=EventDeleteView.as_view('delete'),
    methods=['GET']
)

# from flask import Blueprint, abort, redirect, render_template, flash, url_for
# from .models import Event, Group, db
# from .forms import EventEditForm
# from werkzeug.exceptions import NotFound

# bp = Blueprint("event", __name__, url_prefix="/event")


# @bp.route('/', methods=['GET'])
# def list():
#     events = Event.query.all()
#     return render_template('event/index.html', events=events)


# @bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
# @bp.route('/edit/<int:id>', methods=['GET', 'POST'])
# def edit(id):
#     if id is None:
#         event = Event()
#     else:
#         event = Event.query.filter_by(id=id).first()
#         if event is None:
#             abort(NotFound)

#     form = EventEditForm(obj=event)
#     form.groups.query = Group.query.all()

#     if form.validate_on_submit():
#         form.populate_obj(event)
#         if id is None:
#             db.session.add(event)
#         db.session.commit()
#         flash(f'Event "{event.name}" wurde erfolgreich gespeichert.')
#         return redirect(url_for('event.list'))

#     return render_template('event/edit.html', form=form)


# @bp.route('/delete/<int:id>', methods=['GET'])
# def delete(id):
#     event = Event.query.filter_by(id=id).first()
#     if event is None:
#         abort(NotFound)
#     else:
#         db.session.delete(event)
#         db.session.commit()
#         flash(f'Event "{event.name}" wurde erfolgreich gelöscht.')
#         return redirect(url_for('event.list'))
