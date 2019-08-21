from flask import Blueprint, abort, redirect, render_template, url_for
from .models import db, Event
from .forms import EventEditForm
from .views import ListView, CreateEditView, DeleteView
from . import security
from werkzeug.exceptions import NotFound

bp = Blueprint("event", __name__, url_prefix="/event")


@bp.route('/<int:event_id>/participants', methods=['GET'])
@security.login_required
def list_participants(event_id):
    event = Event.query.filter_by(id=event_id).first()
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
@security.login_required
def send_invitations(event_id):
    event = Event.query.filter_by(id=event_id).first()
    if event is None:
        abort(NotFound)
    else:
        event.send_invitations = True
        db.commit()

        from . import send_invitations
        send_invitations()
        return redirect(url_for('event.list_participants', event_id=event_id))


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
