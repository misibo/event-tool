from flask import Blueprint, abort, redirect, render_template, flash
from .models import Group, db_session
from .forms import GroupEditForm
from werkzeug.exceptions import NotFound

bp = Blueprint("group", __name__, url_prefix="/group",
               template_folder='templates/group')


@bp.route('/', methods=['GET'])
def index():
    groups = db_session.query(Group).all()
    return render_template('index.html', groups=groups)


@bp.route('/edit', methods=['GET', 'POST'], defaults={'id': None})
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
        db_session.commit(group)
        flash(f'Gruppe {group.name} wurde erfolgreich gespeichert.')
        redirect('group')

    return render_template('form.html', form=form)


@bp.route('/edit/<int:id>', methods=['DELETE'])
def delete(id):
    group = db_session.query(Group).filter_by(id=id).first()
    if group is None:
        abort(NotFound)
    else:
        db_session.remove(group)
        db_session.commit()
        redirect('group')
