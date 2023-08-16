import numpy as np
import dataclasses
import os
from dataclasses import dataclass, field
from vtda_alert_pipeline.alert import Alert
from vtda_alert_pipeline.filter_base import Filter


@dataclass
class FilterList:
    """Container class to store all filters to run on an object.
    """
    
    filters: List = field(default_factory=List)
        
    def add_filter(self, filt, index=None):
        """Add filter to list at location 'index'. If index is None, append to end
        of list.
        """
        assert type(filt) == Filter
        
        if index is None:
            self.filters.append(filt)
        else:
            self.filters.insert(index, filt)
          
    def setup_all_filters(self):
        """Run setup for all filters in list.
        """
        for filt in self.filters:
            filt.setup(lc)
            
    def apply_all_filters(self, lc):
        """Apply all filters in list and aggregate the properties.
        """
        for filt in self.filters:
            filt.run(lc)
            
        