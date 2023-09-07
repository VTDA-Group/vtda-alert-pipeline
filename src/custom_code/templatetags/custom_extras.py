from datetime import datetime, timedelta

from astroplan import moon_illumination
from astropy import units as u
from astropy.coordinates import Angle, get_moon, SkyCoord
from astropy.time import Time
from django import template
from django.conf import settings
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
import numpy as np
from plotly import offline
from plotly import graph_objs as go

from tom_observations.utils import get_sidereal_visibility
from tom_targets.models import Target, TargetExtra, TargetList
from tom_targets.forms import TargetVisibilityForm
from urllib.parse import urlencode
from tom_alerts.alerts import get_service_class, get_service_classes
from django.db import IntegrityError
from django.contrib import messages


register = template.Library()


@register.inclusion_tag('tom_alerts/partials/requery_broker_data_button.html', takes_context=True)
def requery_broker_data_button(context):
    current_mjd = 60194 # TODO: unhard-code this
    default_params = {
        'ra': 180.0,
        'dec': 0.1,
        'sr': 180.0,
        'nobs__gt': 5,
        'mag__min': 12.0,
        'mag__max': 20.0,
        'mjd__gt': current_mjd - 30.0,
        'max_alerts': 100,
    }

    broker_name = 'ANTARES' # hard-coded for now
    broker = get_service_class(broker_name)()

    errors = []
    for alert in broker.fetch_alerts(default_params):
        try:
            #print(alert)
            #generic_alert = broker.to_generic_alert(alert)
            #print(generic_alert.id)
            #full_alert = broker.fetch_alert(generic_alert.id)
            target, _, aliases = broker.to_target(alert)
            target.save(names=aliases)
            #broker_class().process_reduced_data(target, json.loads(cached_alert))
    
        except IntegrityError:
                print('Unable to save alert, target with that name already exists.')
                #errors.append(target.name)
                
    