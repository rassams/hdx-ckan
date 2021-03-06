'''
Created on Febr 17, 2020

@author: Dan


'''
import mock
import logging as logging
import ckan.model as model
import ckan.plugins.toolkit as tk
import ckan.logic as logic
import unicodedata
import ckan.lib.helpers as h
import json

import ckanext.hdx_theme.tests.hdx_test_base as hdx_test_base
import ckanext.hdx_theme.tests.hdx_test_with_inds_and_orgs as hdx_test_with_inds_and_orgs
import ckanext.hdx_users.helpers.permissions as ph
import ckanext.hdx_users.helpers.tokens as tkh
import ckanext.hdx_users.model as user_model

from nose.tools import (assert_equal,
                        assert_true,
                        assert_false,
                        assert_not_equal)

log = logging.getLogger(__name__)
NotFound = logic.NotFound


class TestHDXControllerPage(hdx_test_with_inds_and_orgs.HDXWithIndsAndOrgsTest):

    # @classmethod
    # def _load_plugins(cls):
    #     try:
    #         hdx_test_base.load_plugin('hdx_users hdx_user_extra hdx_package hdx_org_group hdx_theme')
    #     except Exception as e:
    #         log.warn('Module already loaded')
    #         log.info(str(e))

    @classmethod
    def _get_action(cls, action_name):
        return tk.get_action(action_name)

    @classmethod
    def _create_test_data(cls, create_datasets=True, create_members=False):
        super(TestHDXControllerPage, cls)._create_test_data(create_datasets=True, create_members=True)

    def _get_url(self, url, apikey=None):
        if apikey:
            page = self.app.get(url, headers={
                'Authorization': unicodedata.normalize('NFKD', apikey).encode('ascii', 'ignore')})
        else:
            page = self.app.get(url)
        return page

    @mock.patch('ckanext.hdx_theme.util.mail.send_mail')
    @mock.patch('ckanext.hdx_package.actions.get.hdx_mailer.mail_recipient')
    def test_onboarding(self, mocked_mail_recipient, mocked_send_mail):

        # step 1 register
        url = h.url_for(controller='ckanext.hdx_users.controllers.mail_validation_controller:ValidationController',
                        action='register_email')
        params = {'email': 'newuser@hdx.org', 'nosetest': 'true'}
        res = self.app.post(url, params)
        assert_true(json.loads(res.body)['success'])

        user = model.User.get('newuser@hdx.org')

        assert_true(user is not None)
        assert_true(user.password is None)

        # step 2 validate
        token = tkh.token_show({}, {'id': user.id})
        url = '/user/validate/' + token.get('token')
        res = self.app.get(url)
        assert '<label for="field-email">Your Email Address</label>' in res.body
        assert 'id="recaptcha"' in res.body
        assert 'value="newuser@hdx.org"' in res.body

        # step 3 details
        context = {'model': model, 'session': model.Session, 'auth_user_obj': user}
        url = h.url_for(controller='ckanext.hdx_users.controllers.mail_validation_controller:ValidationController',
                        action='register_details')

        try:
            res = self.app.post(url, {})
            assert False
        except KeyError, ex:
            assert True

        try:
            res = self.app.post(url, {
                'first-name': 'firstname',
                'last-name': 'lastname',
                'password': 'passpass',
                'name': 'newuser',
                'email': 'newuser@hdx.org',
                'login': 'newuser@hdx.org',
                'id': '123123123123'
            })
            assert False
        except AttributeError, ex:
            assert '\'NoneType\' object has no attribute \'name\'' in ex.message
            assert True

        try:
            res = self.app.post(url, {
                'first-name': 'firstname',
                'last-name': 'lastname',
                'password': 'passpass',
                'name': 'newuser',
                'login': 'newuser@hdx.org',
                'id': user.id
            })
            assert '"Email": "Missing value"' in res.body
        except Exception, ex:
            assert True

        try:
            res = self.app.post(url, {
                'first-name': 'firstname',
                'last-name': 'lastname',
                'password': 'passpass',
                'name': 'testsysadmin',
                'email': 'newuser@hdx.org',
                'login': 'newuser@hdx.org',
                'id': user.id
            })
            assert 'That login name is not available' in res.body
        except Exception, ex:
            assert False

        try:
            res = self.app.post(url, {
                'first-name': 'firstname',
                'last-name': 'lastname',
                'password': 'passpass',
                'email': 'newuser@hdx.org',
                'login': 'newuser@hdx.org',
                'id': user.id
            })
            assert "Missing value" in res.body
        except Exception, ex:
            assert True

        try:
            res = self.app.post(url, {
                'first-name': 'firstname',
                'password': 'pass',
                'name': 'newuser',
                'email': 'newuser@hdx.org',
                'login': 'newuser@hdx.org',
                'id': user.id
            })
            assert False
        except KeyError, ex:
            assert True

        params = {
            'first-name': 'firstname',
            'last-name': 'lastname',
            'password': 'passpass',
            'name': 'newuser',
            'email': 'newuser@hdx.org',
            'login': 'newuser@hdx.org',
            'id': user.id
        }
        try:
            res = self.app.post(url, params)
        except Exception, ex:
            assert False
        assert 'true' in res
        updated_user = model.User.get('newuser@hdx.org')
        assert updated_user.name == params.get('name')
        assert updated_user.id == params.get('id')
        assert updated_user.display_name == params.get('first-name') + " " + params.get('last-name')
        assert updated_user.password is not None
        assert updated_user.sysadmin is False
        assert updated_user.email == params.get('email')
        res = self._get_action('user_extra_show')(context, {'user_id': user.id})
        assert res
        assert self._get_user_extra_by_key(res, user_model.HDX_ONBOARDING_DETAILS) == 'True'


        # step 4 follow
        url = h.url_for(controller='ckanext.hdx_users.controllers.mail_validation_controller:ValidationController',
                        action='follow_details')

        try:
            res = self.app.post(url, {})
            assert False
        except KeyError, ex:
            assert 'id' in ex.message

        params = {
            'id': user.id
        }
        try:
            res = self.app.post(url, params)
        except Exception, ex:
            assert False
        assert 'true' in res
        res = self._get_action('user_extra_show')(context, {'user_id': user.id})
        assert res
        assert self._get_user_extra_by_key(res, user_model.HDX_ONBOARDING_FOLLOWS) == 'True'

        # step 5b request_membership
        url = h.url_for(controller='ckanext.hdx_users.controllers.mail_validation_controller:ValidationController',
                        action='request_membership')

        try:
            res = self.app.post(url, {})
            assert '"message": "Unauthorized to create user"' in res.body
        except Exception, ex:
            assert True

        params = {
            'org_id': 'hdx-test-org',
            'message': "please add me to your organization",
            'save': u'save',
            'role': u'member',
            'group': 'hdx-test-org'
        }

        auth = {'Authorization': str(user.apikey)}
        try:
            res = self.app.post(url, params, extra_environ=auth)
            assert '{"success": true}' in res.body
        except Exception, ex:
            assert False

    def _get_user_extra_by_key(self, user_extras, key):
        ue_show_list = [d.get('value') for i, d in enumerate(user_extras) if d['key'] == key]
        return ue_show_list[0]
