from flask import render_template, request, current_app
from flask.views import View
# from .models import db


class ListView(View):

    filters = []
    sorts = []
    model = None
    template = None

    def sort_from_url(self, query):

        params = request.args

        for column in self.sorts:
            if column in params:
                if params.get(column) == 'asc':
                    params = query.order_by(getattr(self.model, column).asc())
                elif params.get(column) == 'desc':
                    query = query.order_by(getattr(self.model, column).desc())

        return query

    def dict_replace(self, dict1, dict2):
        for key, val in dict2.items():
            if key in dict1:
                dict1[key] = val
        return dict1

    def get_sort_url_params(self):
        return self.dict_replace(dict.fromkeys(self.sorts), request.args.to_dict())

    def filter_from_url(query):
        return query

    def dispatch_request(self):

        query = self.model.query
        query = self.sort_from_url(query)
        pagination = query.paginate(per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
        return render_template(self.template, pagination=pagination, sort=self.get_sort_url_params())
