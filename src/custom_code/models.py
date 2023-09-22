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

    tns = models.BooleanField(
        help_text="Whether to query TNS catalog"
    )
    sn_type = models.CharField(
        max_length=100, help_text="The supernova type to check for."
    )

    
    #class Meta:
    #    ordering = ('-created', 'name',)

    def __str__(self):
        return self.name
    
    
class QuerySet(models.Model):
    """Set of query properties and tags.
    """
    name = models.CharField(
        max_length=100,
        help_text="The query name"
    )
    project = models.OneToOneField(
        ProjectTargetList, on_delete=models.CASCADE
    )

    def get_all_properties(self):
        """Get all associated QueryProperty objects.
        """
        properties = []
        for query_property in QueryProperty.objects.all():
            if query_property.queryset == self:
                properties.append(query_property)
        return properties
    
    def get_all_tags(self):
        """Get all associated QueryTag objects.
        """
        tags = []
        for query_tag in QueryTag.objects.all():
            if query_tag.queryset == self:
                tags.append(query_tag)
        return tags
    
    def generate_antares_query(self):
        """Generate ANTARES query string from
        properties and tags.
        """
        props = self.get_all_properties()
        tags = self.get_all_tags()
        
        # TODO: allow for ORs (at moment it's all ANDs)
        query = {
            "query": {
                "bool": {
                    "must": []
                }
            }
        }
        for prop in props:
            query["query"]["bool"]["must"].append(
                prop.generate_antares_query_dict()
            )
        for tag in tags:
            query["query"]["bool"]["must"].append(
                tag.generate_antares_query_dict()
            )
        return query


class QueryProperty(models.Model):
    """Class representing a property to restrict during a query. 
    """
    antares_name = models.CharField(
        max_length=100,
        help_text="The property name when queried from ANTARES"
    )
    min_value = models.FloatField(
        help_text="Minimum value",
        null=True,
    )
    max_value = models.FloatField(
        help_text="Maximum value",
        null=True,
    )
    categorical = models.BooleanField(
        help_text="Whether property value is categorical (as opposed to continuous)",
        default=False,  
    )
    # TODO: allow multiple target values in future
    target_value = models.CharField(
        max_length=100,
        help_text="Target property value if categorical",
        null=True,
    )
    queryset = models.ForeignKey(
        QuerySet, on_delete=models.CASCADE
    )
    
    class Meta: # assert no repeat properties per QuerySet
        constraints = [
            models.UniqueConstraint(
                fields=['queryset', 'antares_name'],
                name='no_repeat_query_properties'
            )
        ]
        
    def generate_antares_query_dict(self):
        """Generate query snippet for property.
        """
        if self.categorical:
            query_dict = {
                "match": {
                    f"properties.{self.antares_name}": self.target_value
                }
            }
        else:
            sub_dict = {}
            
            if self.min_value is not None:
                sub_dict['gte'] = self.min_value
            if self.max_value is not None:
                sub_dict['lte'] = self.max_value
                
            if self.antares_name in ["ra", "dec"]: # why are they named differently :((((
                query_dict = {
                    "range": {
                        f"{self.antares_name}": sub_dict
                    }
                }
            else:
                query_dict = {
                    "range": {
                        f"properties.{self.antares_name}": sub_dict
                    }
                }
        return query_dict
    
    
class QueryTag(models.Model):
    """Class representing a tag to restrict during a query. 
    """
    antares_name = models.CharField(
        max_length=100,
        help_text="The tag name when queried from ANTARES"
    )
    queryset = models.ForeignKey(
        QuerySet, on_delete=models.CASCADE
    )
    
    class Meta: # assert no repeat properties per QuerySet
        constraints = [
            models.UniqueConstraint(
                fields=['queryset', 'antares_name'],
                name='no_repeat_query_tags'
            )
        ]
        
    def generate_antares_query_dict(self):
        """Generate query snippet for property.
        """
        query_dict = {
            "term": {
                "tags": f"{self.antares_name}"
            }
        }       
        return query_dict

