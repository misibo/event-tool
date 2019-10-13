from flask import Blueprint, current_app, render_template, request, flash, redirect

from .forms import UserEditForm
from .models import User, db
from .security import admin_required
from .views import CreateEditView, DeleteView, ListView
import pytz

bp = Blueprint("user", __name__, url_prefix="/user")

tz = pytz.timezone('Europe/Zurich')

@bp.route('/<string:username>')
def view(username):
    user = User.query.\
        filter(User.username == username).\
        first_or_404()
    return render_template('user/user.html', user=user)

@bp.route('/list')
@admin_required
def list():
        pagination = User.query.\
            order_by_request(User.username, 'order.username').\
            order_by_request(User.first_name, 'order.first_name').\
            order_by_request(User.family_name, 'order.family_name').\
            order_by_request(User.last_login, 'order.last_login').\
            order_by_request(User.modified, 'order.modified').\
            order_by_request(User.email, 'order.email').\
            filter_by_request(User.role, 'filter.role', User.Role.get_values()).\
            search_by_request([User.username, User.first_name, User.family_name, User.email], 'search').\
            paginate(
                per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE']
            )

        return render_template(
            'user/list.html',
            pagination=pagination,
            args=request.args.to_dict(),
            tz=pytz.timezone('Europe/Zurich'),
            UserRoles=User.Role
        )

@bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
        user = User()
        form = UserEditForm(obj=user)

        if form.validate_on_submit():
            form.populate_obj(user)
            user.registered = tz.localize(datetime.now())
            user.modified = tz.localize(datetime.now())
            db.session.add(user)
            db.session.commit()
            flash(f'Neuer Benutzer {user.get_fullname()} erstellt.', 'success')
            return redirect(request.referrer or url_for('user.list'))

        return render_template('user/edit.html', form=form, user=user)

@bp.route('/edit/<int:id>', methods=['GET','POST'])
@admin_required
def edit(id):
    user = User.query.get_or_404(id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        form.populate_obj(user)
        user.modified = tz.localize(datetime.now())
        db.session.commit()
        flash(f'Benutzer {user.get_fullname()} gespeichert.', 'success')
        return redirect(request.referrer or url_for('user.list'))

    return render_template('user/edit.html', form=form, user=user)

@bp.route('/delete/<int:id>')
@admin_required
def delete(id):
    user = User.query.get_or_404(id)
    flash(f'Benutzer {user.get_fullname()} gelöscht.', 'danger')
    db.session.delete(user)
    db.session.commit()
