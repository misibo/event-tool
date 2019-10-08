from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, abort)

from . import mailing
from .forms import GroupEditForm, GroupMemberForm
from .models import Group, GroupMember, User, db
from .security import login_required
from .views import CreateEditView, DeleteView, ListView

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

# become group member
@bp.route('/join/<int:id>', methods=['POST'])
@login_required
def join(id):
    role = request.form['role']

    if role == GroupMember.Role.LEADER and not g.user.can_manage():
        abort(403)

    group = Group.query.get_or_404(id)
    member = GroupMember(
        group=group,
        user=g.user,
        joined=pytz.utc.localize(datetime.utcnow()),
        role=role)
    db.session.add(m)
    db.session.commit()

    mailing.send_invitations()

    flash(f'Du bist jetzt {member.get_role_label()} der Gruppe {group.name}!', 'success')

    return redirect(request.referrer or '/')

# change membership role
@bp.route('/member/edit/<int:id>', methods=['POST'])
@login_required
def member_edit(id):
    member = GroupMember.query.get_or_404(id)
    role = request.form['role']

    if (role == GroupMember.Role.LEADER or member.user_id != g.user.id) and \
            not g.user.can_manage():
        abort(403)

    member.role = role
    db.session.commit()

    mailing.send_invitations()

    flash(f'Du bist jetzt {member.get_role_label()} der Gruppe {group.name}!', 'success')

    return redirect(request.referrer or '/')


@bp.route('/member/leave/<int:id>')
@login_required
def member_leave(id):
    member = GroupMember.query.get_or_404()

    if member.user_id != g.user.id and not g.user.can_manage():
        abort(403)

    db.session.delete(member)
    db.session.commit()

    flash(f'Du hast die Gruppe {group.name} verlassen.', 'warning')

    return redirect(request.referrer or '/')

@bp.route('/members/<int:id>')
@login_required
def members(id):
    group = Group.query.get_or_404(id)
    pagination = GroupMember.query.\
        join(GroupMember.user).\
        filter(GroupMember.group_id == id).\
        filter_by_request(GroupMember.role, 'filter.role', GroupMember.Role.get_choices().keys()).\
        order_by_request(User.first_name, 'order.first_name').\
        order_by_request(User.family_name, 'order.family_name').\
        search_by_request([User.first_name, User.family_name], 'search').\
        paginate(
            per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE']
        )

    return render_template('group/members.html', pagination=pagination, args={**request.args.to_dict(), **{'id': group.id}}, group=group)


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
