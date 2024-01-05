import base64
from io import BytesIO

from PIL import Image
from django import template
from plotly import graph_objs as go
from plotly import offline

register = template.Library()


@register.inclusion_tag('tom_targets/partials/target_host.html', takes_context=True)
def host_info_for_target(context, target):
    """
    Given a ``Target``, returns host info associated with that ``Target``
    """
    print("START")
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
    if host is not None:
        datums = host.add_spectra()
    else:
        datums = []

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
