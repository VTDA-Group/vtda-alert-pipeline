from django.views.generic.base import TemplateView, View
from tom_observations.models import Target
from django.contrib.auth.mixins import LoginRequiredMixin

class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        return {'targets': Target.objects.all()}

            
        
    