from django.db import models

from tom_common.hooks import run_hook
from tom_targets.models import models, TargetList


class ProjectTargetList(TargetList):
    """
    Class representing a list of targets for a specific project in a TOM.
    Extends the TargetList class.

    :param name: The name of the target list
    :type name: str

    :param targets: Set of ``Target`` objects associated with this ``TargetList``

    :param created: The time at which this target list was created.
    :type created: datetime

    :param modified: The time at which this target list was modified in the TOM database.
    :type modified: datetime
    """
    # Note from Kaylee: apparently in Django you can't override attributes of non-abstract classes!
    # May change TargetList and ProjectTargetList to both inherit from mutual abstract class in future
    #name = models.CharField(max_length=200, help_text='The name of the Project.')

    class Meta:
        ordering = ('-created', 'name',)

    def __str__(self):
        return self.name
    
    def query_params(self):
        """Define custom query parameters assuming ANTARES broker.
        """
        pass
    
    def criteria(self, target):
        """Any further project criteria that can not be fed into query_params.
        Takes in the Target object and returns boolean whether it passes criteria
        or not.
        """
        pass
