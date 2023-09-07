from django.views.generic.base import RedirectView, TemplateView, View
from tom_observations.models import Target
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from tom_alerts.alerts import get_service_class, get_service_classes
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse



class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        return {'targets': Target.objects.all()}


class RequeryBrokerView(RedirectView):
    #template_name = 'tom_targets/target_list.html'
    
    def get(self, request, *args, **kwargs):

        current_mjd = 60194 # TODO: unhard-code this
        default_params = {
            'ra': 180.0,
            'dec': 0.1,
            'sr': 360.0,
            'nobs__gt': 5,
            'mag__min': 12.0,
            'mag__max': 20.0,
            'mjd__gt': current_mjd - 30.0,
            'max_alerts': 1000,
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
                #target.save(names=aliases)
                #broker_class().process_reduced_data(target, json.loads(cached_alert))

            except IntegrityError:
                    print('Unable to save alert, target with that name already exists.')
                    #errors.append(target.name)
                    
        return HttpResponseRedirect(reverse('targets:list'))
