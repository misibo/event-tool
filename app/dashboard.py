from flask import Blueprint, flash, g, render_template, redirect, url_for

from .forms import AccountForm
from .models import User, db, Event, GroupMember
from .security import login_required

import pytz

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route('/', methods=['GET', 'POST'])
def index():  # no login required
    upcoming_events = db.session.query(Event).all()

    if g.user:
        memberships = {m.group: m for m in g.user.memberships}
    else:
        memberships = None

    return render_template(
        'dashboard/main.html', 
        upcoming_events=upcoming_events, tz=pytz.timezone('Europe/Zurich'), 
        g=g, memberships=memberships)
