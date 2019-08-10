from flask import Blueprint, abort, redirect, render_template, flash, url_for
from .models import Group, db_session
from .forms import GroupEditForm
from werkzeug.exceptions import NotFound

bp = Blueprint("group", __name__, url_prefix="/group",
               template_folder='templates/group')


@bp.route('/', methods=['GET'])
def list():
    groups = db_session.query(Group).all()
    return render_template('index.html', groups=groups)


@bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if id is None:
        group = Group()
    else:
        group = db_session.query(Group).filter_by(id=id).first()
        if group is None:
            abort(NotFound)

    form = GroupEditForm(obj=group)

    if form.validate_on_submit():
        form.populate_obj(group)
        if id is None:
            db_session.add(group)
        db_session.commit()
        flash(f'Gruppe "{group.name}" wurde erfolgreich gespeichert.')
        return redirect(url_for('group.list'))

    return render_template('edit.html', form=form)


@bp.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    group = db_session.query(Group).filter_by(id=id).first()
    if group is None:
        abort(NotFound)
    else:
        db_session.delete(group)
        db_session.commit()
        flash(f'Gruppe "{group.name}" wurde erfolgreich gelöscht.')
        return redirect(url_for('group.list'))
