'''
Created on Jan 13, 2015

@author: alexandru-m-g
'''

import json

import ckan.controllers.organization as org
import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.common as common
import ckan.new_authz as new_authz

from ckan.common import c, request, _
import ckan.lib.helpers as h

import ckanext.hdx_org_group.helpers.organization_helper as helper
import ckanext.hdx_org_group.controllers.custom_org_controller as custom_org
import ckanext.hdx_search.controllers.search_controller as search_controller

from ckan.controllers.api import CONTENT_TYPES

abort = base.abort
render = base.render

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
get_action = logic.get_action

response = common.response

class HDXOrganizationController(org.OrganizationController, search_controller.HDXSearchController):
    def index(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        try:
            self._check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if c.userobj:
            context['user_id'] = c.userobj.id
            context['user_is_admin'] = c.userobj.sysadmin
            context['auth_user_obj'] = c.userobj

        q = c.q = request.params.get('q', '')
        page = request.params.get('page', 1)
        limit = int(request.params.get('limit', 25))
        sort_option = request.params.get('sort', 'title asc')

        reset_thumbnails = request.params.get('reset_thumbnails', 'false')

        data_dict = {
            'all_fields': True,
            'sort': sort_option if sort_option in ['title asc', 'title desc'] else 'title asc',
            # Custom sorts will throw an error here
            'q': q,
            'reset_thumbnails': reset_thumbnails,
        }

        all_orgs = get_action('organization_list')(context, data_dict)

        all_orgs = helper.sort_results_case_insensitive(all_orgs, sort_option)

        c.featured_orgs = helper.hdx_get_featured_orgs(context, data_dict)

        def pager_url(page=None):
            if sort_option:
                url = h.url_for(
                    'organizations_index', q=q, page=page, sort=sort_option, limit=limit)+'#organizationsSection'
            else:
                url = h.url_for('organizations_index', q=q, page=page, limit=limit)+'#organizationsSection'
            return url

        c.page = h.Page(
            collection=all_orgs,
            page=page,
            url=pager_url,
            items_per_page=limit
        )

        return base.render('organization/index.html')

    def read(self, id, limit=20):
        group_type = self._get_group_type(id.split('@')[0])
        if group_type != self.group_type:
            abort(404, _('Incorrect group type'))

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True}
        data_dict = {'id': id}

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            context['include_datasets'] = False
            c.group_dict = self._action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        # If custom_org set to true, redirect to the correct route
        if self.custom_org_test(c.group_dict['extras']):
            Org = custom_org.CustomOrgController()
            return Org.org_read(id)
        else:
            org_info = self._get_org(id)
            c.full_facet_info = self._get_dataset_search_results(org_info['name'])
            if self._is_facet_only_request():
                response.headers['Content-Type'] = CONTENT_TYPES['json']
                return json.dumps(c.full_facet_info)
            else:
                # self._read(id, limit)
                return render(self._read_template(c.group_dict['type']))

    def _get_org(self, org_id):
        group_type = 'organization'

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True}
        data_dict = {'id': org_id}

        try:
            context['include_datasets'] = False
            result = get_action(
                'hdx_light_group_show')(context, data_dict)

            return result

        except NotFound:
            abort(404, _('Org not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read org %s') % id)

        return {}

    def _get_dataset_search_results(self, org_code):

        user = c.user or c.author
        ignore_capacity_check = False
        is_org_member = (user and
                         new_authz.has_user_permission_for_group_or_org(org_code, user, 'read'))
        if is_org_member:
            ignore_capacity_check = True

        package_type = 'dataset'

        suffix = '#datasets-section'

        params_nopage = {
            k: v for k, v in request.params.items() if k != 'page'}

        def pager_url(q=None, page=None):
            params = params_nopage
            params['page'] = page
            return h.url_for('organization_read', id=org_code, **params) + suffix

        fq = 'organization:"{}"'.format(org_code)
        facets = {
            'vocab_Topics': _('Topics')
        }
        full_facet_info = self._search(package_type, pager_url, additional_fq=fq, additional_facets=facets,
                                       ignore_capacity_check=ignore_capacity_check)
        full_facet_info.get('facets', {}).pop('organization', {})

        c.other_links['current_page_url'] = h.url_for('organization_read', id=org_code)

        return full_facet_info

    def custom_org_test(self, org):
        if [o.get('value', None) for o in org if o.get('key', '') == 'custom_org']:
            return True
        return False

    def new(self, data=None, errors=None, error_summary=None):
        group_type = self._guess_group_type(True)
        if data:
            data['type'] = group_type

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'save': 'save' in request.params,
                   'parent': request.params.get('parent', None)}
        try:
            self._check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a group'))

        if context['save'] and not data:
            return self._save_new(context, group_type)

        data = data or {}
        if not data.get('image_url', '').startswith('http'):
            data.pop('image_url', None)

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'new'}

        self._setup_template_variables(context, data, group_type=group_type)
        c.form = render(self._group_form(group_type=group_type),
                        extra_vars=vars)
        return render(self._new_template(group_type))

    def edit(self, id, data=None, errors=None, error_summary=None):
        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'save': 'save' in request.params,
                   'for_edit': True,
                   'parent': request.params.get('parent', None)
                   }
        data_dict = {'id': id}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            old_data = self._action('group_show')(context, data_dict)
            c.grouptitle = old_data.get('title')
            c.groupname = old_data.get('name')
            data = data or old_data
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')

        group = context.get("group")
        c.group = group
        c.group_dict = self._action('group_show')(context, data_dict)

        try:
            self._check_access('group_update', context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'edit'}

        self._setup_template_variables(context, data, group_type=group_type)
        c.form = render(self._group_form(group_type), extra_vars=vars)
        return render(self._edit_template(c.group.type))
