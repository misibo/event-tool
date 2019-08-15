from flask import current_app, flash, render_template, request, redirect, url_for
from flask.views import View
from .models import db


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
        pagination = query.paginate(
            per_page=current_app.config['PAGINATION_ITEMS_PER_PAGE'])
        return render_template(self.template, pagination=pagination, sort=self.get_sort_url_params())


class CreateView(View):

    form = None
    model = None
    template = None
    redirect = 'index'

    def dispatch_request(self):

        model = self.model()
        form = self.form(obj=model)

        if form.validate_on_submit():

            form.populate_obj(model)
            db.session.add(model)
            db.session.commit()
            flash('Erstellen erfolgreich.')

            return redirect(url_for(self.redirect))

        return render_template(self.template, form=form)


class EditView(View):

    form = None
    model = None
    template = None
    redirect = 'index'

    def dispatch_request(self, id):

        model = self.model.query.get_or_404(id)
        form = self.form(obj=model)

        if form.validate_on_submit():
            form.populate_obj(model)
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


# def register_manager(bp, name, model, list_template, form_template, form, sorts, filters):

#     class ModelListView(ListView):
#         sorts = sorts
#         model = model
#         template = list_template

#     bp.add_url_rule(
#         '/', view_func=ModelListView.as_view('list'), methods=['GET'])

#     class ModelCreateView(CreateView):
#         form = form
#         model = model
#         template = form_template
#         redirect = redirect

#     bp.add_url_rule(
#         '/create', view_func=ModelCreateView.as_view('create'), methods=['GET', 'POST'])

#     class ModelEditView(EditView):
#         form = form
#         model = model
#         template = form_template
#         redirect = redirect

#     bp.add_url_rule('/edit/<int:id>', view_func=ModelEditView.as_view('edit'),
#                     methods=['GET', 'POST'])

#     class ModelDeleteView(DeleteView):
#         model = model
#         redirect = redirect

#     bp.add_url_rule(
#         '/delete/<int:id>', view_func=ModelDeleteView.as_view('delete'), methods=['GET'])
