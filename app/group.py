from flask import Blueprint
from .models import Group
from .forms import GroupEditForm
from .views import ListView, CreateEditView, DeleteView

bp = Blueprint("group", __name__, url_prefix="/group")


class GroupListView(ListView):
    sorts = ['name', 'modified']
    searchable = ['name', 'description']
    model = Group
    template = 'group/index.html'


class GroupCreateEditView(CreateEditView):

    form = GroupEditForm
    model = Group
    template = 'group/edit.html'
    redirect = 'group.list'


class GroupDeleteView(DeleteView):
    model = Group
    redirect = 'group.list'


bp.add_url_rule(
    '/',
    view_func=GroupListView.as_view('list'),
    methods=['GET']
)
bp.add_url_rule(
    '/create',
    defaults={'id': None},
    view_func=GroupCreateEditView.as_view('create'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/edit/<int:id>',
    view_func=GroupCreateEditView.as_view('edit'),
    methods=['GET', 'POST']
)
bp.add_url_rule(
    '/delete/<int:id>',
    view_func=GroupDeleteView.as_view('delete'),
    methods=['GET']
)
