import datetime

import ckan.model as model
import ckan.plugins.toolkit as tk

ValidationError = tk.ValidationError


import ckanext.hdx_theme.tests.hdx_test_with_inds_and_orgs as hdx_test_with_inds_and_orgs


class TestResourceDates(hdx_test_with_inds_and_orgs.HDXWithIndsAndOrgsTest):

    context_sysadmin = {'model': model, 'session': model.Session, 'user': 'testsysadmin'}
    resource_id  = None

    @classmethod
    def setup_class(cls):
        super(TestResourceDates, cls).setup_class()

        dataset_dict = cls._get_action('package_show')(cls.context_sysadmin, {'id': 'test_private_dataset_1'})
        cls.resource_id = dataset_dict['resources'][0]['id']

    def test_data_start_date_validation(self):
        '''
        Tests that date_start_for_data can only be isodate or empty
        '''

        self.__saving_date_filed('date_start_for_data')

    def test_data_start_date_search(self):

        self.__search_by_date_field('date_start_for_data')

    def test_data_end_date_after_start_date_validation(self):
        '''
        Tests that date_end_for_data is after date_start_for_data
        '''

        context_sysadmin = self.context_sysadmin

        future_time = datetime.datetime.utcnow() + datetime.timedelta(weeks=4)

        resource_dict = self._get_action('resource_patch')(context_sysadmin,
                                          {
                                              'id': self.resource_id,
                                              'date_end_for_data': future_time.isoformat()
                                          })

        assert resource_dict.get('date_end_for_data') == future_time.isoformat()

        try:
            self._get_action('resource_patch')(context_sysadmin,
                                               {
                                                   'id': self.resource_id,
                                                   'date_start_for_data': future_time.isoformat()
                                               })
            assert False
        except ValidationError as ve:
            assert True
        except Exception as e:
            assert False

    def test_data_end_date_validation(self):
        '''
        Tests that date_end_for_data can only be isodate or empty
        '''

        self.__saving_date_filed('date_end_for_data')

    def test_data_end_date_search(self):

        self.__search_by_date_field('date_end_for_data')

    def test_special_end_for_data_random_value(self):

        context_sysadmin = self.context_sysadmin

        try:
            self._get_action('resource_patch')(context_sysadmin,
                                               {
                                                   'id': self.resource_id,
                                                   'special_end_for_data': 'DUMMY_STRING'
                                               })
            assert False
        except ValidationError as ve:
            assert True
        except Exception as e:
            assert False

    def test_special_end_for_data_not_together_with_date_end(self):
        '''
        special_end_for_data and date_end_for_data shouldn't both be filled at the same time
        '''
        context_sysadmin = self.context_sysadmin
        try:
            self._get_action('resource_patch')(context_sysadmin,
                                               {
                                                   'id': self.resource_id,
                                                   'date_end_for_data': datetime.datetime.utcnow().isoformat(),
                                                   'special_end_for_data': 'NOW'
                                               })
            assert False
        except ValidationError as ve:
            assert True
        except Exception as e:
            assert False

        resource_dict = self._get_action('resource_patch')(context_sysadmin,
                                           {
                                               'id': self.resource_id,
                                               'date_end_for_data': None,
                                               'special_end_for_data': 'NOW'
                                           })
        assert resource_dict.get('special_end_for_data') == 'NOW'

    def __saving_date_filed(self, date_field):
        context_sysadmin = self.context_sysadmin
        current_time = datetime.datetime.utcnow()
        resource_dict = self._get_action('resource_patch')(context_sysadmin,
                                                           {
                                                               'id': self.resource_id,
                                                               date_field: current_time.isoformat()
                                                           })
        assert resource_dict.get(date_field) == current_time.isoformat()
        try:
            self._get_action('resource_patch')(context_sysadmin,
                                               {
                                                   'id': self.resource_id,
                                                   date_field: 'DUMMY STRING'
                                               })
            assert False
        except ValidationError as e:
            assert True, '{} needs to be a date'.format(date_field)
        del resource_dict[date_field]
        resource_dict2 = self._get_action('resource_update')(context_sysadmin, resource_dict)
        assert not resource_dict2.get(date_field), 'For now, {} shouldn\'t be mandatory'.format(date_field)

    def __search_by_date_field(self, date_field):
        current_time = datetime.datetime.utcnow()
        self._get_action('resource_patch')(self.context_sysadmin,
                                           {
                                               'id': self.resource_id,
                                               date_field: current_time.isoformat()
                                           })
        begin = current_time - datetime.timedelta(minutes=1)
        end = current_time + datetime.timedelta(minutes=1)
        search_dict = {
            'include_private': True,
            'fq': 'res_extras_{}:[{}Z TO {}Z]'.format(date_field, begin.isoformat(), end.isoformat())
        }
        results = self._get_action('package_search')(self.context_sysadmin, search_dict)
        pkg_names = (p.get('name') for p in results.get('results', []))
        assert 'test_private_dataset_1' in pkg_names
