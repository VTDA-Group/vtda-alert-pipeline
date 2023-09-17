from django.views.generic.base import RedirectView, TemplateView, View
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from tom_observations.models import Target
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from tom_alerts.alerts import get_service_class, get_service_classes
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from astropy.time import Time
from guardian.mixins import PermissionListMixin
from django_filters.views import FilterView
from tom_targets.filters import TargetFilter

from custom_code.models import ProjectTargetList
from custom_code.forms import ProjectForm


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
    
    
class ProjectCreateView(CreateView):
    """
    View that handles the creation of ``TargetList`` objects, also known as target groups. Requires authentication.
    """
    form_class = ProjectForm
    model = ProjectTargetList
    template_name = 'tom_targets/project_form.html'
    success_url = reverse_lazy('custom_code:projects')


    def form_valid(self, form):
        """
        Runs after form validation. Saves the target group and assigns the user's permissions to the group.

        :param form: Form data for target creation
        :type form: django.forms.ModelForm
        """
        return super().form_valid(form)
        #project = form.save(commit=False)
        #project.save()
        #return super().form_valid(form)

    

class RequeryBrokerView(RedirectView):
    #template_name = 'tom_targets/target_list.html'
    #model = ProjectTargetList
    
    def save_alerts_to_group(project, broker):
        """Save list of alerts' targets along
        with a certain group tag."""
        params = project.query_params()
        for alert in broker.fetch_alerts(params):
            try:
                target, _, aliases = broker.to_target(alert)
                add_to_project = project.criteria(target)
                if add_to_project:
                    target.save(names=aliases)
                    project.add(target)

            except IntegrityError:
                    print('Unable to save alert, either because ' +
                          'target with that name already exists, or because ' +
                          'there was an error saving target to project.'
                         )                    
                    
        
    def get(self, request, *args, **kwargs):
        
        current_mjd = Time.now().mjd 

        """
        default_params = {
            'ra': 180.0,
            'dec': 0.1,
            'sr': 360.0,
            'nobs__gt': 5,
            'mag__min': 12.0,
            'mag__max': 20.0,
            'mjd__gt': current_mjd - 30.0,
            'max_alerts': 100,
        }
        """

        broker_name = 'ANTARES' # hard-coded for now
        broker = get_service_class(broker_name)()
        
        for project in ProjectTargetList.objects.all():
            save_alerts_to_group(project, broker)
        
                    
        return HttpResponseRedirect(reverse('targets:list'))
