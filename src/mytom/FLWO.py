from crispy_forms.layout import Layout
from django import forms
from tom_observations.facility import BaseRoboticObservationFacility, BaseRoboticObservationForm

class KeplerCamForm(BaseRoboticObservationForm):
    exposure_time = forms.IntegerField()
    exposure_count = forms.IntegerField()
    def layout(self):
        return Layout(
            'exposure_time',
            'exposure_count'
        )

class KeplerCam(BaseRoboticObservationFacility):
    name = 'KeplerCam'
    observation_types = observation_forms = {
        'OBSERVATION': KeplerCamForm
    }
    SITES = {
        'Fred Lawrence Whipple Observatory': {
            'latitude': 31.675330632,
            'longitude': -110.873663172,
            'elevation': 2616
        }
    }

    def data_products(self, observation_id, product_id=None):
       return []

    def get_form(self, observation_type):
        return KeplerCamForm

    def get_observation_status(self, observation_id):
        return ['IN_PROGRESS']

    def get_observation_url(self, observation_id):
        return ''

    def get_terminal_observing_states(self):
        return ['IN_PROGRESS', 'COMPLETED']

    def submit_observation(self, observation_payload):
        print(observation_payload)
        return [1]

    def validate_observation(self, observation_payload):
        pass

    def get_observing_sites(self):
        return self.SITES
