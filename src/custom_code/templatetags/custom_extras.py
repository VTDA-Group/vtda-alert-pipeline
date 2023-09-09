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


                
    