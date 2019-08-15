from flask import Blueprint, abort, redirect, render_template, flash, url_for, current_app, request
from .models import Group, db
from .forms import GroupEditForm
from werkzeug.exceptions import NotFound
# from .views import ListView

bp = Blueprint("group", __name__, url_prefix="/group")


def dict_replace(dict1, dict2):
    for key, val in dict2.items():
        if key in dict1:
            dict1[key] = val
    return dict1


# class GroupListView(ListView):
#     sorts = ['name', 'modified']
#     model = Group
#     template = 'group/index.html'


# bp.add_url_rule('/', view_func=GroupListView.as_view('list'), methods=['GET'])


@bp.route('/', methods=['GET'])
def list():
    data = dict_replace(dict.fromkeys(['name', 'modified']), request.args.to_dict())
    query = Group.query
    if data['name']:
        if data['name'] == 'asc':
            query = query.order_by(getattr(Group, 'name').asc())
        elif data['name'] == 'desc':
            query = query.order_by(getattr(Group, 'name').desc())
    if data['modified']:
        if data['modified'] == 'asc':
            query = query.order_by(getattr(Group, 'modified').asc())
        elif data['modified'] == 'desc':
            query = query.order_by(getattr(Group, 'modified').desc())
    groups = query.paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
    return render_template('group/index.html', groups=groups, data=data)


@bp.route('/create', methods=['GET', 'POST'], defaults={'id': None})
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if id is None:
        group = Group()
    else:
        group = Group.query.filter_by(id=id).first()
        if group is None:
            abort(NotFound)

    form = GroupEditForm(obj=group)

    if form.validate_on_submit():
        form.populate_obj(group)
        if id is None:
            db.session.add(group)
        db.session.commit()
        flash(f'Gruppe "{group.name}" wurde erfolgreich gespeichert.')
        return redirect(url_for('group.list'))

    return render_template('group/edit.html', form=form)


@bp.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    group = Group.query.filter_by(id=id).first()
    if group is None:
        abort(NotFound)
    else:
        db.session.delete(group)
        db.session.commit()
        flash(f'Gruppe "{group.name}" wurde erfolgreich gelöscht.')
        return redirect(url_for('group.list'))
