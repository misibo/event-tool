from datetime import datetime

import pytz
from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, url_for)

from . import mail
from .forms import GroupEditForm, GroupMemberForm, ConfirmDeleteGroupForm
from .models import Event, Group, GroupEventRelation, GroupMember, User, db
from .security import admin_required, login_required, manager_required
from .utils import localtime_to_utc, tz, url_back

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

    members = GroupMember.query.\
        filter(GroupMember.group_id == group.id).\
        join(GroupMember.user).\
        order_by(GroupMember.role.desc()).\
        order_by(User.username.asc()).\
        all()

    upcoming = Event.query.\
            join(GroupEventRelation, (GroupEventRelation.event_id == Event.id) & (GroupEventRelation.group_id == group.id)).\
            filter(Event.start > tz.localize(datetime.now())).\
            order_by(Event.start.asc()).\
            all()

    form = GroupMemberForm()

    membership = None
    if g.user:
        for member in members:
            if member.user_id == g.user.id:
                membership = member
                break

    return render_template(
        'group/group.html',
        group=group,
        members=members,
        pcoming=upcoming,
        GroupMember=GroupMember,
        groupmember_form=form,
        membership=membership
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


@bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@admin_required
def delete(id):
    group = Group.query.get_or_404(id)
    form = ConfirmDeleteGroupForm()

    if form.validate_on_submit():
        if 'confirm' in request.form:
            db.session.delete(group)
            db.session.commit()
            flash(f'Die Gruppe {group.name} wurde gelöscht.', 'success')
        return redirect(url_for('group.list'))

    return render_template('group/delete.html', form=form, group=group)
