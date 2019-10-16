from datetime import datetime

import pytz
from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, url_for)

from . import mailing
from .forms import GroupEditForm
from .models import Group, GroupMember, User, db
from .security import admin_required, login_required, manager_required
from .utils import url_back

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
    db.session.add(member)
    db.session.commit()


    # TODO send mission invitations for user who joined the new group
    # mailing.send_invitations()

    flash(f'Du bist jetzt "{member.get_role_label()}"" der Gruppe "{group.name}"."', 'success')

    return redirect(url_back('group.groups'))


@bp.route('/member/edit/<int:id>', methods=['POST'])
@login_required
def member_edit(id):
    member = GroupMember.query.get_or_404(id)
    role = request.form['role']

    editing = member.user_id != g.user.id

    if (role == GroupMember.Role.LEADER or editing) and \
            not g.user.can_manage():
        abort(403)

    if GroupMember.Role.has_value(role):
        member.role = role
        db.session.commit()

    # TODO mailing.send_invitations()

    if editing:
        flash(f'Mitglied "{member.user.get_fullname()}" hat jetzt die Rolle "{member.get_role_label()}" in der Gruppe "{member.group.name}".', 'success')
    else:
        flash(f'Du bist jetzt "{member.get_role_label()}" der Gruppe "{member.group.name}".', 'success')

    return redirect(url_back('group.groups'))


@bp.route('/member/leave/<int:id>')
@login_required
def member_leave(id):
    member = GroupMember.query.get_or_404(id)

    editing = member.user_id != g.user.id

    if  editing and not g.user.can_manage():
        abort(403)

    if editing:
        flash(f'Mitglied "{member.user.get_fullname()} von der Gruppe "{member.group.name}" entfernt.', 'warning')
    else:
        flash(f'Du hast die Gruppe "{member.group.name}" verlassen.', 'warning')

    db.session.delete(member)
    db.session.commit()

    return redirect(url_back('group.groups'))


@bp.route('/members/<int:id>')
@manager_required
def members(id):
    group = Group.query.get_or_404(id)
    pagination = GroupMember.query.\
        join(GroupMember.user).\
        filter(GroupMember.group_id == id).\
        filter_by_request(GroupMember.role, 'filter.role', GroupMember.Role.get_values()).\
        order_by_request(User.first_name, 'order.first_name').\
        order_by_request(User.family_name, 'order.family_name').\
        search_by_request([User.first_name, User.family_name], 'search').\
        paginate(
            per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE']
        )

    return render_template(
        'group/members.html',
        pagination=pagination,
        args={**request.args.to_dict(), **{'id': group.id}},
        group=group,
        GroupMemberRoles=GroupMember.Role
    )


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
        args=request.args.to_dict()
    )


@bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
        group = Group()
        form = GroupEditForm(obj=group)

        if form.validate_on_submit():
            form.populate_obj(group)
            db.session.add(group)
            db.session.commit()
            flash(f'Gruppe "{group.name}" erstellt.', 'success')
            return redirect(url_back('group.list'))

        return render_template('group/edit.html', form=form, group=group)


@bp.route('/edit/<int:id>', methods=['GET','POST'])
@manager_required
def edit(id):
    group = Group.query.get_or_404(id)
    form = GroupEditForm(obj=group)

    if form.validate_on_submit():
        form.populate_obj(group)
        db.session.commit()
        flash(f'Gruppe "{group.name}" gespeichert.', 'success')
        return redirect(url_back('group.list'))

    return render_template('group/edit.html', form=form, group=group)


@bp.route('/delete/<int:id>')
@admin_required
def delete(id):
    group = Group.query.get_or_404(id)
    db.session.delete(group)
    db.session.commit()
    flash(f'Gruppe "{group.name}" gelöscht.', 'danger')
