from flask import Blueprint, abort, redirect, render_template, flash, url_for, current_app, request
from .models import Group, db
from .forms import GroupEditForm
from werkzeug.exceptions import NotFound
from .views import ListView, CreateView, EditView, DeleteView

bp = Blueprint("group", __name__, url_prefix="/group")


class GroupListView(ListView):
    sorts = ['name', 'modified']
    model = Group
    template = 'group/index.html'


bp.add_url_rule('/', view_func=GroupListView.as_view('list'), methods=['GET'])


class GroupCreateView(CreateView):
    form = GroupEditForm
    model = Group
    template = 'group/edit.html'
    redirect = 'group.list'


bp.add_url_rule(
    '/create', view_func=GroupCreateView.as_view('create'), methods=['GET', 'POST'])


class GroupEditView(EditView):
    form = GroupEditForm
    model = Group
    template = 'group/edit.html'
    redirect = 'group.list'


bp.add_url_rule('/edit/<int:id>', view_func=GroupEditView.as_view('edit'),
                methods=['GET', 'POST'])


class GroupDeleteView(DeleteView):
    model = Group
    redirect = 'group.list'


bp.add_url_rule(
    '/delete/<int:id>', view_func=GroupDeleteView.as_view('delete'), methods=['GET'])
