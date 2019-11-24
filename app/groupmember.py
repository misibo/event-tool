from flask import Blueprint, redirect, flash, render_template, g, url_for, current_app, request
from .security import login_required, manager_required
from .forms import GroupMemberForm, ConfirmForm
from .models import db, Group, GroupMember, User
from .utils import now, url_back

bp = Blueprint("groupmember", __name__, url_prefix="/group")

@bp.route('/<int:id>/join', methods=['GET', 'POST'])
@login_required
def join(id):
    group = Group.query.get_or_404(id)
    form = GroupMemberForm()
    member = GroupMember()
    form.adapt_role_choices(g.user.can_manage())

    if form.validate_on_submit():
        if form.role.data == GroupMember.Role.LEADER and not g.user.can_manage():
            abort(403)

        form.populate_obj(member)
        member.group = group
        member.user = g.user
        member.joined = now
        db.session.add(member)
        db.session.commit()

        # TODO send mission invitations for user who joined the new group
        # mailing.send_invitations()

        flash(f'Du bist jetzt "{member.get_role_label()}"" der Gruppe "{group.name}"."', 'success')

        return redirect(url_for('group.view', slug=group.slug))

    return render_template('groupmember/edit.html', group=group, form=form, member=member)


@bp.route('/member/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    member = GroupMember.query.get_or_404(id)
    form = GroupMemberForm(obj=member)
    editing = member.user_id != g.user.id
    can_manage = g.user.can_manage()
    form.adapt_role_choices(can_manage)

    if editing and not can_manage:
        abort(403)

    if form.validate_on_submit():

        if form.role.data == GroupMember.Role.LEADER and not can_manage:
            abort(403)

        form.populate_obj(member)
        db.session.commit()

        if editing:
            flash(f'Mitglied "{member.user.get_fullname()}" hat jetzt die Rolle "{member.get_role_label()}" in der Gruppe "{member.group.name}".', 'success')
        else:
            flash(f'Du bist jetzt "{member.get_role_label()}" der Gruppe "{member.group.name}".', 'success')

        return redirect(url_back('group.groups'))

    return render_template('groupmember/edit.html', form=form, member=member)


@bp.route('/member/<int:id>/remove', methods=['GET', 'POST'])
@login_required
def remove(id):
    member = GroupMember.query.get_or_404(id)

    editing = member.user_id != g.user.id

    if editing and not g.user.can_manage():
        abort(403)

    form = ConfirmForm()

    if form.validate_on_submit():
        if editing:
            flash(f'Mitglied "{member.user.get_fullname()} von der Gruppe "{member.group.name}" entfernt.', 'warning')
        else:
            flash(f'Du hast die Gruppe "{member.group.name}" verlassen.', 'warning')
        db.session.delete(member)
        db.session.commit()
        return redirect(url_back('group.groups'))

    return render_template('groupmember/remove.html', member=member, form=form)


@bp.route('/<int:id>/member')
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
        'groupmember/members.html',
        pagination=pagination,
        args={**request.args.to_dict(), **{'id': group.id}},
        group=group,
        GroupMemberRoles=GroupMember.Role
    )
