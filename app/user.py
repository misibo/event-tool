from flask import Blueprint, render_template

from .forms import UserEditForm
from .models import User
from .views import CreateEditView, DeleteView, ListView
from . import security

bp = Blueprint("user", __name__, url_prefix="/user")


@bp.route('/view/<int:id>')
# @security.login_required
def view(id):
    user = User.query.get_or_404(id)
    return render_template('user/view.html', user=user)


class UserTableView(ListView):
    sorts = ['username', 'first_name', 'family_name', 'email']
    filters = {'role': User.Role.get_choices().keys()}
    searchable = ['username', 'first_name', 'family_name', 'email']
    model = User
    template = 'user/index.html'


class UserCreateEditView(CreateEditView):
    form = UserEditForm
    model = User
    template = 'user/edit.html'
    redirect = 'user.list'


class UserDeleteView(DeleteView):
    model = User
    redirect = 'user.list'


bp.add_url_rule(
    '/',
    view_func=security.login_required(
        UserTableView.as_view('list'), 
        privilege=User.Role.ADMIN),
    methods=['GET']
)
bp.add_url_rule(
    '/create',
    defaults={'id': None},
    view_func=security.login_required(
        UserCreateEditView.as_view('create'),
        privilege=User.Role.ADMIN),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/edit/<int:id>',
    view_func=security.login_required(
        UserCreateEditView.as_view('edit'),
        privilege=User.Role.ADMIN),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/delete/<int:id>',
    view_func=security.login_required(
        UserDeleteView.as_view('delete'),
        privilege=User.Role.ADMIN),
    methods=['GET']
)
