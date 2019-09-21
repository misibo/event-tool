from flask import Blueprint, current_app,render_template, redirect, request, g, flash

from .security import login_required
from .forms import GroupEditForm
from .models import Group, GroupMember, db
from .views import CreateEditView, DeleteView, ListView
from . import mailing

bp = Blueprint("group", __name__, url_prefix="/group")

@bp.route('/view')
def groups():
    pagination = Group.query.\
        order_by(Group.name.asc()).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
    return render_template('group/groups.html', pagination=pagination)

@bp.route('/view/<int:id>')
@login_required
def view(id):
    group = Group.query.get_or_404(id)
    return render_template('group/group.html', group=group)


@bp.route('/join/<int:id>')
@login_required
def join(id):
    group = Group.query.get_or_404(id)
    m = db.session.query(GroupMember).filter_by(user=g.user, group=group).first()
    if m:
        m.role = GroupMember.Role.MEMBER
    else:
        m = GroupMember(user=g.user, group=group, role=GroupMember.Role.MEMBER)
        db.session.add(m)
    db.session.commit()
    mailing.send_invitations()

    flash(f'Du bist jetzt Mitglied der Gruppe {group.name}!', 'info')

    return redirect(request.referrer or '/')


@bp.route('/watch/<int:id>')
@login_required
def watch(id):
    group = Group.query.get_or_404(id)
    m = db.session.query(GroupMember).filter_by(user=g.user, group=group).first()
    if m:
        m.role = GroupMember.Role.SPECTATOR
    else:
        m = GroupMember(user=g.user, group=group, role=GroupMember.Role.SPECTATOR)
        db.session.add(m)
    db.session.commit()
    mailing.send_invitations()

    flash(f'Du bist jetzt Zuschauer der Gruppe {group.name}!', 'info')

    return redirect(request.referrer or '/')


@bp.route('/leave/<int:id>')
@login_required
def leave(id):
    group = Group.query.get_or_404(id)
    m = db.session.query(GroupMember).filter_by(user=g.user, group=group).first()
    if m:
        db.session.delete(m)
        db.session.commit()

    flash(f'Du bist der Gruppe {group.name} ausgetreten.', 'info')

    return redirect(request.referrer or '/')


class GroupListView(ListView):
    sorts = ['name', 'modified']
    searchable = ['name', 'description']
    model = Group
    template = 'group/index.html'


class GroupCreateEditView(CreateEditView):

    form = GroupEditForm
    model = Group
    template = 'group/edit.html'
    redirect = 'group.list'


class GroupDeleteView(DeleteView):
    model = Group
    redirect = 'group.list'


bp.add_url_rule(
    '/',
    view_func=GroupListView.as_view('list'),
    methods=['GET']
)
bp.add_url_rule(
    '/create',
    defaults={'id': None},
    view_func=GroupCreateEditView.as_view('create'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/edit/<int:id>',
    view_func=GroupCreateEditView.as_view('edit'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/delete/<int:id>',
    view_func=GroupDeleteView.as_view('delete'),
    methods=['GET']
)
