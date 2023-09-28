from django.views.generic.base import RedirectView, TemplateView, View
from django.views.generic.edit import FormView, CreateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from tom_alerts.alerts import get_service_class, get_service_classes
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from astropy.time import Time
from guardian.mixins import PermissionListMixin
from django_filters.views import FilterView
from tom_common.mixins import Raise403PermissionRequiredMixin
from tom_targets.filters import TargetFilter
import marshmallow
import json

from tom_alerts import alerts

from tom_targets.models import Target, TargetList

from custom_code.models import (
    ProjectTargetList,
    QuerySet,
    QueryProperty,
    QueryTag,
    TargetAux
)

from custom_code.forms import ProjectForm
from custom_code.filter_helper import (
    check_type_tns,
    run_anomaly_tag,
    tns_label_dict,
    save_alerts_to_group,
    update_all_hosts
)

def save_params_as_queryset(parameters, project):
    """Converts query dictionary to string for easy saving. Copied over
    from tom_antares."""
    tags = parameters.get('tags')
    nobs_gt = parameters.get('nobs__gt')
    nobs_lt = parameters.get('nobs__lt')
    sra = parameters.get('ra')
    sdec = parameters.get('dec')
    ssr = parameters.get('sr')
    mjd_gt = parameters.get('mjd__gt')
    mjd_lt = parameters.get('mjd__lt')
    mag_min = parameters.get('mag__min')
    mag_max = parameters.get('mag__max')

    # default values
    if nobs_gt is None:
        nobs_gt = 0
    if nobs_lt is None:
        nobs_lt = 1e10
    if mjd_gt is None:
        mjd_gt = 0.0
    if mjd_lt is None:
        mjd_lt = 1e10
    if mag_min is None:
        mag_min = 0
    if mag_max is None:
        mag_max = 40

    qs = project.queryset

    nobs_prop = QueryProperty(
        antares_name="num_mag_values",
        min_value = nobs_gt,
        max_value = nobs_lt,
        queryset = qs
    )
    nobs_prop.save()

    mjd_prop = QueryProperty(
        antares_name="newest_alert_observation_time",
        min_value = 0.0,
        max_value = mjd_lt,
        queryset = qs
    )
    mjd_prop.save()

    mjd_prop2 = QueryProperty(
        antares_name="oldest_alert_observation_time",
        min_value = mjd_gt,
        max_value = 1e10,
        queryset = qs
    )
    mjd_prop2.save()

    mag_prop = QueryProperty(
        antares_name="newest_alert_magnitude",
        min_value = mag_min,
        max_value = mag_max,
        queryset = qs
    )
    mag_prop.save()

    sra_prop = QueryProperty(
        antares_name="ra",
        min_value = sra-ssr,
        max_value = sra+ssr,
        queryset = qs
    )
    sra_prop.save()

    sdec_prop = QueryProperty(
        antares_name="dec",
        min_value = sdec-ssr,
        max_value = sdec+ssr,
        queryset = qs
    )
    sdec_prop.save()

    if tags:
        for t in tags:
            tag = QueryTag(
                antares_name=t,
                queryset = qs
            )
            tag.save()
        
    if 'LAISS_RFC_AD_filter' in tags:
        anom_prop = QueryProperty(
            antares_name="LAISS_RFC_anomaly_score",
            min_value = 25.0,
            queryset = qs
        )
        anom_prop.save()
        
        
class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        return {'targets': Target.objects.all()}


class TargetListView(PermissionListMixin, FilterView):
    """
    View for listing targets in the TOM. Only shows targets that the user is authorized to view. Requires authorization.
    """
    template_name = 'tom_targets/target_list.html'
    paginate_by = 25
    strict = False
    model = Target
    filterset_class = TargetFilter
    permission_required = 'tom_targets.view_target'
    ordering = ['-created']

    def get_context_data(self, *args, **kwargs):
        """
        Adds the number of targets visible, the available ``TargetList`` objects if the user is authenticated, and
        the query string to the context object.

        :returns: context dictionary
        :rtype: dict
        """
        context = super().get_context_data(*args, **kwargs)
        context['target_count'] = context['paginator'].count
        # hide target grouping list if user not logged in
        context['groupings'] = (TargetList.objects.all()
                                if self.request.user.is_authenticated
                                else TargetList.objects.none())
        context['query_string'] = self.request.META['QUERY_STRING']
        return context
    

class ProjectView(ListView):
    """
    View that handles the display of ``TargetList`` objects, also known as target groups. Requires authorization.
    """
    #permission_required = 'tom_targets.view_targetlist'
    template_name = 'tom_targets/projects.html'
    model = ProjectTargetList
    paginate_by = 25
    
    
class ProjectCreateView(FormView):
    """
    View that handles the creation of ``TargetList`` objects, also known as target groups. Requires authentication.
    """
    form_class = ProjectForm
    #model = ProjectTargetList
    template_name = 'tom_targets/project_form.html'
    success_url = reverse_lazy('custom_code:projects')

            
    def form_valid(self, form):
        """
        Runs after form validation. Saves the target group and assigns the user's permissions to the group.

        :param form: Form data for target creation
        :type form: django.forms.ModelForm
        """
        param_dict = form.cleaned_data
        name = form.cleaned_data['project_name']
        tns = form.cleaned_data['tns']
        sn_type = form.cleaned_data['sn_type']
    
        project = ProjectTargetList(
            name=name,
            tns=tns,
            sn_type=sn_type,
        )
        project.save()

        qs = QuerySet(
            name=f"qs_{name}",
            project=project,
        )
        qs.save()
        save_params_as_queryset(param_dict, project)
        return super().form_valid(form)

    
class ProjectDeleteView(DeleteView):
    """
    View that handles the deletion of ``ProjectTargetList`` objects, also known as target groups. Requires authorization.
    """
    model = ProjectTargetList
    template_name = 'tom_targets/projecttargetlist_confirm_delete.html'
    success_url = reverse_lazy('custom_code:projects')

    
    
class RequeryBrokerView(RedirectView):
                    
        
    def get(self, request, *args, **kwargs):
        
        current_mjd = Time.now().mjd 

        broker_name = 'ANTARES' # hard-coded for now
        broker = get_service_class(broker_name)()
        
        for project in ProjectTargetList.objects.all():
            save_alerts_to_group(project, broker)
            
        update_all_hosts()
                    
        return HttpResponseRedirect(reverse('targets:list'))

    
class TargetDetailView(Raise403PermissionRequiredMixin, DetailView):
    """
    View that handles the display of the target details. Requires authorization.
    """
    permission_required = 'tom_targets.view_target'
    model = Target

    def get_context_data(self, *args, **kwargs):
        """
        Adds the ``DataProductUploadForm`` to the context and prepopulates the hidden fields.

        :returns: context object
        :rtype: dict
        """
        context = super().get_context_data(*args, **kwargs)
        observation_template_form = ApplyObservationTemplateForm(initial={'target': self.get_object()})
        if any(self.request.GET.get(x) for x in ['observation_template', 'cadence_strategy', 'cadence_frequency']):
            initial = {'target': self.object}
            initial.update(self.request.GET)
            observation_template_form = ApplyObservationTemplateForm(
                initial=initial
            )
        observation_template_form.fields['target'].widget = HiddenInput()
        context['observation_template_form'] = observation_template_form
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles the GET requests to this view. If update_status is passed into the query parameters, calls the
        updatestatus management command to query for new statuses for ``ObservationRecord`` objects associated with this
        target.

        :param request: the request object passed to this view
        :type request: HTTPRequest
        """
        update_status = request.GET.get('update_status', False)
        if update_status:
            if not request.user.is_authenticated:
                return redirect(reverse('login'))
            target_id = kwargs.get('pk', None)
            out = StringIO()
            call_command('updatestatus', target_id=target_id, stdout=out)
            messages.info(request, out.getvalue())
            add_hint(request, mark_safe(
                              'Did you know updating observation statuses can be automated? Learn how in'
                              '<a href=https://tom-toolkit.readthedocs.io/en/stable/customization/automation.html>'
                              ' the docs.</a>'))
            return redirect(reverse('tom_targets:detail', args=(target_id,)))

        obs_template_form = ApplyObservationTemplateForm(request.GET)
        if obs_template_form.is_valid():
            obs_template = ObservationTemplate.objects.get(pk=obs_template_form.cleaned_data['observation_template'].id)
            obs_template_params = obs_template.parameters
            obs_template_params['cadence_strategy'] = request.GET.get('cadence_strategy', '')
            obs_template_params['cadence_frequency'] = request.GET.get('cadence_frequency', '')
            params = urlencode(obs_template_params)
            return redirect(
                reverse('tom_observations:create',
                        args=(obs_template.facility,)) + f'?target_id={self.get_object().id}&' + params)

        return super().get(request, *args, **kwargs)