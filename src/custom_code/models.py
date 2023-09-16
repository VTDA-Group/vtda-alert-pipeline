from django.db import models
from tom_targets.models import TargetList

# Create your models here.
class Project(TargetList):
    """Extends TargetList model to also include criteria functions.
    """
    def query_params(self):
        """Define custom query parameters assuming ANTARES broker.
        """
        pass
    
    def criteria(self):
        """Any further project criteria that can not be fed into query_params.
        """
        pass
    