from flask import current_app, flash, render_template, request, redirect, url_for
from flask.views import View
from sqlalchemy import or_
from .models import db


class ListView(View):

    sorts = []
    filters = {}
    searchable = []
    model = None
    template = None

    # def dict_expand(dict):

    #     def recursion(dict, keys, value):
    #         key = keys.pop(0)
    #         if key not in dict:
    #             dict[key] = {}
    #         if len(keys) >= 1:
    #             dict[key] = recursion(dict[key], keys, value)
    #         else:
    #             dict[key] = value
    #         return dict

    #     res = {}

    #     for key, value in dict.items():
    #         keys = key.split('.')
    #         res = recursion(res, keys, value)

    #     return res

    # def dict_flatten(d, path=''):
    #     res = {}
    #     for key, value in d.items():
    #         if type(value) is dict:
    #             res = {**res, **dict_flatten(value, f'{path}{key}.')}
    #         else:
    #             res[path+key] = value
    #     return res

    # def dict_replace(self, dict1, dict2):
    #     for key, val in dict2.items():
    #         if key in dict1:
    #             dict1[key] = val
    #     return dict1

    def sort(self, query):
        args = {}
        for key in self.sorts:
            args_key = f'sort.{key}'
            value = request.args.get(args_key)
            if value:
                attr = getattr(self.model, key)
                if value == 'asc':
                    query = query.order_by(attr.asc())
                elif value == 'desc':
                    query = query.order_by(attr.desc())
                args[args_key] = value

        return query, args

    # TODO test filter (with enum)
    def filter(self, query):
        args = {}
        for key in self.filters.keys():
            args_key = f'filter.{key}'
            value = request.args.get(args_key)
            if value and value in self.filters[key]():
                args[args_key] = value
                query = query.filter(getattr(self.model, key) == value)
        return query, args

    def search(self, query):
        args = {}
        search = request.args.get('search')
        if search:
            args['search'] = search
            searches = []
            for column in self.searchable:
                searches.append(getattr(self.model, column).contains(search))
            query = query.filter(or_(*searches))
        return query, args

    def dispatch_request(self):

        query = self.model.query

        query, sort_args = self.sort(query)
        query, filter_args = self.filter(query)
        query, search_args = self.search(query)

        pagination = query.paginate(
            per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE']
        )

        return render_template(
            self.template,
            pagination=pagination,
            args={**sort_args, **filter_args, **search_args}
        )


class CreateEditView(View):

    form = None
    model = None
    template = None
    redirect = 'index'

    def dispatch_request(self, id):

        if id is None:
            model = self.model()
        else:
            model = self.model.query.get_or_404(id)

        form = self.form(obj=model)

        if form.validate_on_submit():
            form.populate_obj(model)
            if id is None:
                db.session.add(model)
            db.session.commit()
            flash('Speichern erfolgreich.')
            return redirect(url_for(self.redirect))

        return render_template(self.template, form=form)


class DeleteView(View):

    model = None
    redirect = 'index'

    def dispatch_request(self, id):

        model = self.model.query.get_or_404(id)
        db.session.delete(model)
        db.session.commit()
        flash('Löschen erfolgreich.')

        return redirect(url_for(self.redirect))
