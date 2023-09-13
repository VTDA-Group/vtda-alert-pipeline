import logging
import requests

import antares_client
from antares_client.search import get_by_ztf_object_id
from astropy.time import Time, TimezoneInfo
from crispy_forms.layout import Div, Fieldset, Layout, HTML
from django import forms
import marshmallow

from tom_alerts.alerts import GenericBroker, GenericQueryForm, GenericAlert
from tom_targets.models import Target, TargetName

from tom_dataproducts.models import DataProduct, ReducedDatum


logger = logging.getLogger(__name__)

ANTARES_BASE_URL = 'https://antares.noirlab.edu'
ANTARES_API_URL = 'https://api.antares.noirlab.edu'
ANTARES_TAG_URL = ANTARES_API_URL + '/v1/tags'
superphot_types = ['SN Ia', 'SN II', 'SN IIn', 'SLSN', 'SN Ibc']
tns_label_dict = {'SN Ia':'Ia', 'SN II':'II', 'SN IIn': 'IIn', 'SLSN': 'SLSN', 'SN Ibc': 'Ibc'}

def get_available_tags():
    tags = [{'type': 'tag', 'attributes': {'filter_version_id': 1, 'description': 'A hard-coded test.'}, 'id': 'superphot_plus_classified', 'file': {'self': './'}}]
    return tags


def get_tag_choices():
    tags = get_available_tags()
    return [(s['id'], s['id']) for s in tags]

def get_sn_types():
    sn_type_selection = [(s, s) for s in superphot_types]
    sn_type_selection.append(('None','None'))
    return sn_type_selection




class NovelBrokerForm(GenericQueryForm):
    # define form content
    tag = forms.MultipleChoiceField(required=False, choices=get_tag_choices)
    sn_type = forms.MultipleChoiceField(required=False, choices=get_sn_types)
    tns = forms.BooleanField(required=False)

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
        min_value=0.0
    )
    dec = forms.FloatField(
        required=False,
        label='Dec',
        widget=forms.TextInput(attrs={'placeholder': 'Dec (Degrees)'}),
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
    esquery = forms.JSONField(
        required=False,
        label='Elastic Search query in JSON format',
        widget=forms.TextInput(attrs={'placeholder': '{"query":{}}'}),
    )
    max_alerts = forms.FloatField(
        label='Maximum number of alerts to fetch',
        widget=forms.TextInput(attrs={'placeholder': 'Max Alerts'}),
        min_value=1,
        initial=20
    )

    # cone_search = ConeSearchField()
    # api_search_tags = forms.MultipleChoiceField(choices=get_tag_choices)

    # TODO: add section for searching API in addition to consuming stream

    # TODO: add layout
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            self.common_layout,
            HTML('''
                <p>
                This currently cannot be edited via a form!!
            </p>
            '''),
            HTML('<hr/>'),
            HTML('<p style="color:blue;font-size:30px">Simple query form</p>'),
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
                'View Filters',
                'tag'
            ),
            Fieldset(
                'Specific Type?',
                'sn_type'
            ),
            Fieldset(
                'Include TNS?',
                'tns'
            ),
            Fieldset(
                'Max Alerts',
                'max_alerts'
            ),
            HTML('<hr/>'),
            HTML('<p style="color:blue;font-size:30px">Advanced query</p>'),
            Fieldset(
                 '',
                 'esquery'
            ),
            HTML('''
                <p>
                Please see <a href="https://noao.gitlab.io/antares/client/tutorial/searching.html">ANTARES
                 Documentation</a> for a detailed description of advanced searches.
                </p>
            ''')
            # HTML('<hr/>'),
            # Fieldset(
            #     'API Search',
            #     'api_search_tags'
            # )
        )

    def clean(self):
        cleaned_data = super().clean()

        # Ensure all cone search fields are present
        if any(cleaned_data[k] for k in ['ra', 'dec', 'sr']) and not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            raise forms.ValidationError('All of RA, Dec, and Search Radius must be included to perform a cone search.')
        # default value for cone search
        '''
        if not all(cleaned_data[k] for k in ['ra', 'dec', 'sr']):
            cleaned_data['ra'] = 180.
            cleaned_data['dec'] = 0.
            cleaned_data['sr'] = 180.
        '''
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

        # Ensure using either a stream or the advanced search form
        # if not (cleaned_data['tag'] or cleaned_data['esquery']):
        #    raise forms.ValidationError('Please either select tag(s) or use the advanced search query.')
        # Ensure using either a stream or the advanced search form
        if not (cleaned_data['tag']):
            raise forms.ValidationError(
                'Please either enter the ZTF ID, or select tag(s), or use the advanced search query.'
            )

        return cleaned_data


class NovelBroker(GenericBroker):
    name = 'NovelBroker'
    form = NovelBrokerForm

    @classmethod
    def alert_to_dict(cls, locus):
        """
        Note: The ANTARES API returns a Locus object, which in the TOM Toolkit
        would otherwise be called an alert.

        This method serializes the Locus into a dict so that it can be cached by the view.
        """
        return {
            'locus_id': locus.locus_id,
            'ra': locus.ra,
            'dec': locus.dec,
            'properties': locus.properties,
            'tags': locus.tags,
            # 'lightcurve': locus.lightcurve.to_json(),
            'catalogs': locus.catalogs,
            'alerts': [{
                'alert_id': alert.alert_id,
                'mjd': alert.mjd,
                'properties': alert.properties
            } for alert in locus.alerts]
        }

    def fetch_alerts(self, parameters: dict) -> iter:
        tags = parameters.get('tag')
        sn_type = parameters.get('sn_type')
        tns = parameters.get('tns')
        nobs_gt = parameters.get('nobs__gt')
        nobs_lt = parameters.get('nobs__lt')
        sra = parameters.get('ra')
        sdec = parameters.get('dec')
        ssr = parameters.get('sr')
        mjd_gt = parameters.get('mjd__gt')
        mjd_lt = parameters.get('mjd__lt')
        mag_min = parameters.get('mag__min')
        mag_max = parameters.get('mag__max')
        elsquery = parameters.get('esquery')
        ztfid = parameters.get('ztfid')
        max_alerts = parameters.get('max_alerts', 20)
        if ztfid:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "properties.ztf_object_id": ztfid
                                }
                            }
                        ]
                    }
                }
            }
        elif elsquery:
            query = elsquery
        else:
            filters = []

            if nobs_gt or nobs_lt:
                nobs_range = {'range': {'properties.num_mag_values': {}}}
                if nobs_gt:
                    nobs_range['range']['properties.num_mag_values']['gte'] = nobs_gt
                if nobs_lt:
                    nobs_range['range']['properties.num_mag_values']['lte'] = nobs_lt
                filters.append(nobs_range)

            if mjd_lt:
                mjd_lt_range = {'range': {'properties.newest_alert_observation_time': {'lte': mjd_lt}}}
                filters.append(mjd_lt_range)

            if mjd_gt:
                mjd_gt_range = {'range': {'properties.oldest_alert_observation_time': {'gte': mjd_gt}}}
                filters.append(mjd_gt_range)

            if mag_min or mag_max:
                mag_range = {'range': {'properties.newest_alert_magnitude': {}}}
                if mag_min:
                    mag_range['range']['properties.newest_alert_magnitude']['gte'] = mag_min
                if mag_max:
                    mag_range['range']['properties.newest_alert_magnitude']['lte'] = mag_max
                filters.append(mag_range)

            if sra and ssr:  # TODO: add cross-field validation
                ra_range = {'range': {'ra': {'gte': sra-ssr, 'lte': sra+ssr}}}
                filters.append(ra_range)

            if sdec and ssr:  # TODO: add cross-field validation
                dec_range = {'range': {'dec': {'gte': sdec-ssr, 'lte': sdec+ssr}}}
                filters.append(dec_range)

            if tags:
                filters.append({'terms': {'tags': tags}})


            query = {
                    "query": {
                        "bool": {
                            "filter": filters
                        }
                    }
                }
        loci = antares_client.search.search(query)
#        if ztfid:
#            loci = get_by_ztf_object_id(ztfid)
        alerts = []
        while len(alerts) < max_alerts:
            locus = next(loci)
            skippy = True
            try:   
                locus = next(loci)
                if sn_type[0] != 'None':
                    print(sn_type)
                    print('should not be here')
                    if tns:
                        if 'tns_public_objects' in locus.catalogs:
                            if 'type' in locus.catalog_objects['tns_public_objects']:
                                if locus.catalog_objects['tns_public_objects']['type'] == tns_label_dict[sn_type[0]]:
                                    skippy = False
                    if locus.properties['superphot_plus_class'] == sn_type[0]:
                        skippy = False
            except (marshmallow.exceptions.ValidationError, StopIteration):
                break
            if not skippy:
                alerts.append(self.alert_to_dict(locus))
        return iter(alerts)

    def fetch_alert(self, id):
        alert = get_by_ztf_object_id(id)
        return alert
    
    # TODO: This function
    def process_reduced_data(self, target, alert=None):
        """Implemented in this version, NOT in the original ANTARES filter.
        """
        oid = target.name
        alerts = self.fetch_alert(oid).alerts

        for alert in alerts:
            mjd = Time(alert.mjd, format='mjd', scale='utc')
            properties = alert.properties
            is_upper_lim = 'ant_mag' not in properties
            if not is_upper_lim:
                value = {
                    'filter': properties['ant_passband'],
                    'magnitude': properties['ant_mag'],
                    'error': properties['ant_magerr'],
                }
            else:
                value = {
                    'filter': properties['ant_passband'],
                    'limit': properties['ant_maglim'],
                }
            ReducedDatum.objects.get_or_create(
                timestamp=mjd.to_datetime(TimezoneInfo()),
                value=value,
                source_name=self.name,
                source_location=oid,
                data_type='photometry',
                target=target
            )


    def to_target(self, alert: dict) -> Target:
        target = Target.objects.create(
            name=alert['properties']['ztf_object_id'],
            type='SIDEREAL',
            ra=alert['ra'],
            dec=alert['dec'],
        )
        antares_name = TargetName(target=target, name=alert['locus_id'])
        aliases = [antares_name]
        if alert['properties'].get('horizons_targetname'):  # TODO: review if any other target names need to be created
            aliases.append(TargetName(name=alert['properties'].get('horizons_targetname')))
        return target, [], aliases

    def to_generic_alert(self, alert):
        url = f"{ANTARES_BASE_URL}/loci/{alert['locus_id']}"
        timestamp = Time(
            alert['properties'].get('newest_alert_observation_time'), format='mjd', scale='utc'
        ).to_datetime(timezone=TimezoneInfo())
        return GenericAlert(
            timestamp=timestamp,
            url=url,
            id=alert['locus_id'],
            name=alert['properties']['ztf_object_id'],
            ra=alert['ra'],
            dec=alert['dec'],
            mag=alert['properties'].get('newest_alert_magnitude', ''),
            score=alert['alerts'][-1]['properties'].get('ztf_rb', '')
        )
