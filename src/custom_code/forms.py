from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from astropy.time import Time, TimezoneInfo
import logging
import requests
import marshmallow

from django import forms
from django.conf import settings
from django.shortcuts import reverse
from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit, Fieldset, HTML

from tom_observations.models import ObservationRecord
from tom_alerts.alerts import GenericBroker, GenericQueryForm, GenericAlert
from tom_targets.models import Target, TargetName
from tom_antares.antares import get_tag_choices

from custom_code.models import ProjectTargetList
from custom_code.filter_helper import (
    get_sn_types
)


class ProjectForm(forms.Form):
    # define form content
    project_name = forms.CharField(required=True)
    sn_types = forms.MultipleChoiceField(
        required=False,
        choices=get_sn_types,
        widget=forms.CheckboxSelectMultiple,
    )
    tns = forms.BooleanField(required=False)

    tags = forms.MultipleChoiceField(
        required=True,
        choices=get_tag_choices,
        widget=forms.CheckboxSelectMultiple,
    )
    nobs__gt = forms.IntegerField(
        required=False,
        label='Detections Lower',
        widget=forms.TextInput(attrs={'placeholder': 'Min number of measurements'})
    )
    nobs__lt = forms.IntegerField(
        required=False,
        label='Detections Upper',
        widget=forms.TextInput(attrs={'placeholder': 'Max number of measurements'})
    )
    ra = forms.FloatField(
        required=False,
        label='RA',
        widget=forms.TextInput(attrs={'placeholder': 'RA (Degrees)'}),
        max_value=360.0,
        min_value=0.0
    )
    dec = forms.FloatField(
        required=False,
        label='Dec',
        widget=forms.TextInput(attrs={'placeholder': 'Dec (Degrees)'}),
        max_value=90.0,
        min_value=-90.0
    )
    sr = forms.FloatField(
        required=False,
        label='Search Radius',
        widget=forms.TextInput(attrs={'placeholder': 'radius (Degrees)'}),
        min_value=0.0
    )
    mjd__gt = forms.FloatField(
        required=False,
        label='Min date of alert detection ',
        widget=forms.TextInput(attrs={'placeholder': 'Date (MJD)'}),
        min_value=0.0
    )
    mjd__lt = forms.FloatField(
        required=False,
        label='Max date of alert detection',
        widget=forms.TextInput(attrs={'placeholder': 'Date (MJD)'}),
        min_value=0.0
    )
    mag__min = forms.FloatField(
        required=False,
        label='Min magnitude of the latest alert',
        widget=forms.TextInput(attrs={'placeholder': 'Min Magnitude'}),
        min_value=0.0
    )
    mag__max = forms.FloatField(
        required=False,
        label='Max magnitude of the latest alert',
        widget=forms.TextInput(attrs={'placeholder': 'Max Magnitude'}),
        min_value=0.0
    )

    # cone_search = ConeSearchField()
    # api_search_tags = forms.MultipleChoiceField(choices=get_tag_choices)

    # TODO: add section for searching API in addition to consuming stream

    # TODO: add layout
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Create'))
        self.helper.layout = Layout(
            HTML('''
                <p>
                Users can create a Project object by (1) designating the ANTARES query
                parameters to filter by and (2) include any additional criteria as Python
                code. Additional code MUST take in a Target object and output a boolean value.
            </p>
            '''),
            HTML('<hr/>'),
            Fieldset(
                'Project Name',
                'project_name'
            ),
            HTML('<p style="color:blue;font-size:30px">ANTARES query parameters</p>'),
            Fieldset(
                'Alert timing',
                Div(
                    Div(
                        'mjd__gt',
                        css_class='col',
                    ),
                    Div(
                        'mjd__lt',
                        css_class='col',
                    ),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Number of measurements',
                Div(
                    Div(
                        'nobs__gt',
                        css_class='col',
                    ),
                    Div(
                        'nobs__lt',
                        css_class='col',
                    ),
                    css_class='form-row',
                )
            ),
            Fieldset(
                'Brightness of the latest alert',
                Div(
                    Div(
                        'mag__min',
                        css_class='col',
                    ),
                    Div(
                        'mag__max',
                        css_class='col',
                    ),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'Cone Search',
                Div(
                    Div(
                        'ra',
                        css_class='col'
                    ),
                    Div(
                        'dec',
                        css_class='col'
                    ),
                    Div(
                        'sr',
                        css_class='col'
                    ),
                    css_class='form-row'
                )
            ),
            Fieldset(
                'View Tags',
                'tags'
            ),
            Fieldset(
                'Specific Type?',
                'sn_types'
            ),
            Fieldset(
                'Include TNS?',
                'tns'
            ),
        )
        '''
            Fieldset(
                'Max Alerts',
                'max_alerts'
            ),
        )
        
            HTML('<hr/>'),
            HTML('<p style="color:blue;font-size:30px">Additional Criteria</p>'),
            Fieldset(
                 '',
                 'criteria'
            ),
            
        )
        '''

    def clean(self):
        cleaned_data = super().clean()

        # Ensure all cone search fields are present
        if any(cleaned_data[k] for k in ['ra', 'dec', 'sr']) and not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            raise forms.ValidationError('All of RA, Dec, and Search Radius must be included to perform a cone search.')
        # default value for cone search
        if not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            cleaned_data['ra'] = 180.
            cleaned_data['dec'] = 0.
            cleaned_data['sr'] = 180.
        # Ensure alert timing constraints have sensible values
        if all(cleaned_data[k] for k in ['mjd__lt', 'mjd__gt']) and cleaned_data['mjd__lt'] <= cleaned_data['mjd__gt']:
            raise forms.ValidationError('Min date of alert detection must be earlier than max date of alert detection.')

        # Ensure number of measurement constraints have sensible values
        if (all(cleaned_data[k] for k in ['nobs__lt', 'nobs__gt'])
                and cleaned_data['nobs__lt'] <= cleaned_data['nobs__gt']):
            raise forms.ValidationError('Min number of measurements must be smaller than max number of measurements.')

        # Ensure magnitude constraints have sensible values
        if (all(cleaned_data[k] for k in ['mag__min', 'mag__max'])
                and cleaned_data['mag__max'] <= cleaned_data['mag__min']):
            raise forms.ValidationError('Min magnitude must be smaller than max magnitude.')

        return cleaned_data
