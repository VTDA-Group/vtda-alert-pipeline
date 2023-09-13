from django.views.generic.base import RedirectView, TemplateView, View
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


class RequeryBrokerView(RedirectView):
    #template_name = 'tom_targets/target_list.html'
    
    def get(self, request, *args, **kwargs):

        current_mjd = nt = Time.now().mjd 

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

        broker_name = 'ANTARES' # hard-coded for now
        broker = get_service_class(broker_name)()

        errors = []
        for alert in broker.fetch_alerts(default_params):
            try:
                target, _, aliases = broker.to_target(alert)
                target.save(names=aliases)

            except IntegrityError:
                    print('Unable to save alert, target with that name already exists.')
                    #errors.append(target.name)
                    
        return HttpResponseRedirect(reverse('targets:list'))
