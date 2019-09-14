from flask import Blueprint, render_template

from .forms import UserEditForm
from .models import User
from .views import CreateEditView, DeleteView, ListView

bp = Blueprint("user", __name__, url_prefix="/user")


@bp.route('/<int:id>/view')
def view(id):
    return render_template('user/view.html')


class UserListView(ListView):
    sorts = ['username', 'first_name', 'family_name', 'email']
    filters = {'permission': User.Permission.__members__}
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
    view_func=UserListView.as_view('list'),
    methods=['GET']
)
bp.add_url_rule(
    '/create',
    defaults={'id': None},
    view_func=UserCreateEditView.as_view('create'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/edit/<int:id>',
    view_func=UserCreateEditView.as_view('edit'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/delete/<int:id>',
    view_func=UserDeleteView.as_view('delete'),
    methods=['GET']
)
