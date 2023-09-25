from datetime import datetime, timedelta

from astroplan import moon_illumination
from astropy import units as u
from astropy.coordinates import Angle, get_moon, SkyCoord
from astropy.time import Time
import mpld3
from PIL import Image
from io import BytesIO
import base64


from django import template
from django.conf import settings
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
import numpy as np
from plotly import offline
from plotly import graph_objs as go
import matplotlib.pyplot as plt

from tom_observations.utils import get_sidereal_visibility
from tom_targets.models import TargetExtra, Target, TargetList
from tom_targets.forms import TargetVisibilityForm
from urllib.parse import urlencode
from tom_alerts.alerts import get_service_class, get_service_classes
from django.db import IntegrityError
from django.contrib import messages
from tom_dataproducts.models import ReducedDatum

from custom_code.models import ProjectTargetList

register = template.Library()

@register.inclusion_tag('tom_targets/partials/target_host.html', takes_context=True)
def host_info_for_target(context, target):
    """
    Given a ``Target``, returns host info associated with that ``Target``
    """
    print("START")
    host = target.aux_info.host
    
    if host is None:
        target.aux_info.search_for_host_galaxy()
        host = target.aux_info.host
    
    if host is None:
        host_name = "N/A"
        host_ra = "N/A"
        host_dec = "N/A"
    else:
        host_name = host.name
        host_ra = host.ra
        host_dec = host.dec
        host.add_spectra()
        
    # get spectrum
    datums = host.add_spectra()
        
    plot_data = []
    for value in datums:
       
        plot_data.append(
            go.Scatter(
                x=value[0],
                y=value[1],
            )
        )
        
    layout = go.Layout(
        height=600,
        width=700,
        xaxis=dict(
            tickformat="d"
        ),
        yaxis=dict(
            tickformat=".1eg"
        )
    )
    spectrum_fig = offline.plot(
        go.Figure(data=plot_data, layout=layout),
        output_type='div',
        show_link=False
    )
    
    # get image - do not save!
    if host is None:
        im = Image.new('RGB', (240, 240))
    else:
        im = host.add_image()
    buffer = BytesIO()
    im.save(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')
        
    return {
        'host_name': host_name,
        'host_ra': host_ra,
        'host_dec': host_dec,
        'spectra': spectrum_fig,
        'image': graphic,
    }
