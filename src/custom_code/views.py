from django.views.generic.base import RedirectView, TemplateView, View
from django.views.generic.edit import FormView, CreateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from tom_alerts.alerts import get_service_class, get_service_classes
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from astropy.time import Time
from guardian.mixins import PermissionListMixin
from django_filters.views import FilterView
from django.shortcuts import get_object_or_404
from tom_common.mixins import Raise403PermissionRequiredMixin
from tom_targets.filters import TargetFilter
import antares_client
import marshmallow
import json

from tom_targets.models import Target, TargetList
from custom_code.models import ProjectTargetList, TargetAux

from custom_code.forms import ProjectForm
from custom_code.filter_helper import (
    check_type_tns,
    run_anomaly_tag,
    tns_label_dict,
)
    


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


    def generate_query_string(self, parameters):
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
        
        filters = []

        if nobs_gt or nobs_lt:
            nobs_range = {"range": {"properties.num_mag_values": {}}}
            if nobs_gt:
                nobs_range["range"]["properties.num_mag_values"]["gte"] = nobs_gt
            if nobs_lt:
                nobs_range["range"]["properties.num_mag_values"]["lte"] = nobs_lt
            filters.append(nobs_range)

        if mjd_lt:
            mjd_lt_range = {"range": {"properties.newest_alert_observation_time": {"lte": mjd_lt}}}
            filters.append(mjd_lt_range)

        if mjd_gt:
            mjd_gt_range = {"range": {"properties.oldest_alert_observation_time": {"gte": mjd_gt}}}
            filters.append(mjd_gt_range)

        if mag_min or mag_max:
            mag_range = {"range": {"properties.newest_alert_magnitude": {}}}
            if mag_min:
                mag_range["range"]["properties.newest_alert_magnitude"]["gte"] = mag_min
            if mag_max:
                mag_range["range"]["properties.newest_alert_magnitude"]["lte"] = mag_max
            filters.append(mag_range)

        if sra and ssr:  # TODO: add cross-field validation
            ra_range = {"range": {"ra": {"gte": sra-ssr, "lte": sra+ssr}}}
            filters.append(ra_range)

        if sdec and ssr:  # TODO: add cross-field validation
            dec_range = {"range": {"dec": {"gte": sdec-ssr, "lte": sdec+ssr}}}
            filters.append(dec_range)

        if tags:
            filters.append({"term": {"tags": tags[0]}})

        query = {
                "query": {
                    "bool": {
                        "filter": filters
                    }
                }
            }
        return json.dumps(query)
            
    def form_valid(self, form):
        """
        Runs after form validation. Saves the target group and assigns the user's permissions to the group.

        :param form: Form data for target creation
        :type form: django.forms.ModelForm
        """
        param_dict = form.cleaned_data
        query_str = self.generate_query_string(param_dict)
        name = form.cleaned_data['project_name']
        tns = form.cleaned_data['tns']
        sn_type = form.cleaned_data['sn_type']
        project = ProjectTargetList(
            name=name,
            tns=tns,
            sn_type=sn_type,
            query=query_str,
        )
        project.save()
        return super().form_valid(form)

    
class ProjectDeleteView(DeleteView):
    """
    View that handles the deletion of ``ProjectTargetList`` objects, also known as target groups. Requires authorization.
    """
    model = ProjectTargetList
    template_name = 'tom_targets/projecttargetlist_confirm_delete.html'
    success_url = reverse_lazy('custom_code:projects')

    
    
class RequeryBrokerView(RedirectView):

    def save_alerts_to_group(self, project, broker):
        """Save list of alerts' targets along
        with a certain group tag."""
        MAX_ALERTS = 20
        query = json.loads(project.query)
        loci = antares_client.search.search(query)
        sn_type = project.sn_type[2:-2] # TODO: fix this
        tns = project.tns
        # TODO: make this not atrocious, will be fixed when query string is not
        #directly saved to model

        tags = query['query']['bool']['filter'][-1]['term']['tags']

        n_alerts = 0
        while n_alerts < MAX_ALERTS:
            try:
                locus = next(loci)
            except (marshmallow.exceptions.ValidationError, StopIteration):
                break
                
            #bandaid solution
            # TODO: fix
            if sn_type not in ['None', '']:
                skippy = True
                if tns and check_type_tns(locus, tns_label_dict[sn_type]):
                    skippy = False
                if ('superphot_plus_class' in locus.properties) & ('superphot_plus_classified' in tags):
                    if locus.properties['superphot_plus_class'] == sn_type:
                        skippy = False
                if 'LAISS_RFC_AD_filter' in tags:
                    if self.run_anomaly_tag(locus):
                        skippy = False
                if skippy:
                    continue
                    
            alert = broker.alert_to_dict(locus)
            try:
                target, _, aliases = broker.to_target(alert)
                target.save(names=aliases)
                target_aux = TargetAux.create(
                    target=target
                )
                
            except IntegrityError:
                print('Target already in database.')
                target = get_object_or_404(
                    Target,
                    name=alert['properties']['ztf_object_id']
                )
            try:
                project.targets.add(target)
                n_alerts += 1   
            except:
                print('Error saving target to project')

           
                    
        
    def get(self, request, *args, **kwargs):
        
        current_mjd = Time.now().mjd 

        broker_name = 'ANTARES' # hard-coded for now
        broker = get_service_class(broker_name)()
        
        for project in ProjectTargetList.objects.all():
            self.save_alerts_to_group(project, broker)
        
                    
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
