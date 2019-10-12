from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, url_for)

from . import mailing
from .forms import GroupEditForm
from .models import Group, GroupMember, User, db
from .security import login_required, manager_required, admin_required
from .views import CreateEditView, DeleteView, ListView
import pytz
import datetime

bp = Blueprint("group", __name__, url_prefix="/group")

@bp.route('/')
def groups():
    pagination = Group.query.\
        order_by(Group.name.asc()).\
        paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
    return render_template('group/groups.html', pagination=pagination)

@bp.route('/<string:slug>')
def view(slug):
    group = Group.query.\
        filter(Group.slug == slug).\
        first_or_404()
    return render_template('group/group.html', group=group, GroupMember=GroupMember)

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
        joined=pytz.utc.localize(datetime.datetime.utcnow()),
        role=role)
    db.session.add(member)
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
    if int(role) in GroupMember.Role.get_choices().keys():
        member.role = role
        db.session.commit()

    # mailing.send_invitations()

    flash(f'Du bist jetzt {member.get_role_label()} der Gruppe {member.group.name}!', 'success')

    return redirect(request.referrer or '/')


@bp.route('/member/leave/<int:id>')
@login_required
def member_leave(id):
    member = GroupMember.query.get_or_404(id)

    if member.user_id != g.user.id and not g.user.can_manage():
        abort(403)

    flash(f'Du hast die Gruppe {member.group.name} verlassen.', 'warning')

    db.session.delete(member)
    db.session.commit()

    return redirect(request.referrer or '/')

@bp.route('/members/<int:id>')
@manager_required
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

@bp.route('/list')
@manager_required
def list():
        pagination = Group.query.\
            order_by_request(Group.name, 'order.name').\
            order_by_request(Group.modified, 'order.modified').\
            search_by_request([Group.name, Group.abstract, Group.details], 'search').\
            paginate(
                per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE']
            )

        return render_template(
            'group/list.html',
            pagination=pagination,
            args=request.args.to_dict(),
            tz=pytz.timezone('Europe/Zurich')
        )

# class GroupListView(ListView):
#     sorts = ['name', 'modified']
#     searchable = ['name', 'description']
#     model = Group
#     template = 'group/index.html'

@bp.route('/create', methods=['POST'])
@admin_required
def create():
        group = Group()
        form = GroupEditForm(obj=group)

        if form.validate_on_submit():
            form.populate_obj(group)
            db.session.add(group)
            db.session.commit()
            flash('Neue Gruppe {group.name} erstellt.')
            return redirect(request.referrer or url_for('group.list'))

        return render_template('group/edit.html', form=form, group=group)

@bp.route('/edit/<int:id>', methods=['GET','POST'])
@manager_required
def edit(id):
    group = Group.query.get_or_404(id)
    form = GroupEditForm(obj=group)

    if form.validate_on_submit():
        form.populate_obj(group)
        db.session.commit()
        flash('Gruppe {group.name} gespeichert.')
        return redirect(request.referrer or url_for('group.list'))

    return render_template('group/edit.html', form=form, group=group)

@bp.route('/delete/<int:id>')
@admin_required
def delete(id):
    group = Group.query.get_or_404(id)
    db.session.delete(group)
    db.session.commit()
    flash('Gruppe {group.name} gelöscht.')


# class GroupCreateEditView(CreateEditView):

#     form = GroupEditForm
#     model = Group
#     template = 'group/edit.html'
#     redirect = 'group.list'


# class GroupDeleteView(DeleteView):
#     model = Group
#     redirect = 'group.list'


# bp.add_url_rule(
#     '/',
#     view_func=GroupListView.as_view('list'),
#     methods=['GET']
# )
# bp.add_url_rule(
#     '/create',
#     defaults={'id': None},
#     view_func=GroupCreateEditView.as_view('create'),
#     methods=['GET', 'POST']
# )
# bp.add_url_rule(
#     '/edit/<int:id>',
#     view_func=GroupCreateEditView.as_view('edit'),
#     methods=['GET', 'POST']
# )
# bp.add_url_rule(
#     '/delete/<int:id>',
#     view_func=GroupDeleteView.as_view('delete'),
#     methods=['GET']
# )
