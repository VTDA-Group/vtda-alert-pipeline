import numpy as np
import dataclasses
import os
from dataclasses import dataclass, field
from inspect import signature
from vtda_alert_pipeline.utils import mag_to_flux

@dataclass
class Alert:
    """Class to store information about each alert.
    """
    
    ID : str
    mjd: float
    ra: float
    dec: float
    magnitude: float
    mag_error: float
    band: str
    
    flux: float = np.nan
    flux_error: float = np.nan
    zeropoint: float = np.nan
    
    #TODO: implement __eq__ and __hash__ functions
    
    def __post_init__(self):
        assert ~np.isnan(self.mjd)
        if np.isnan(self.flux) and ~np.isnan(self.zeropoint):
            self.flux, self.flux_error = mag_to_flux(self.magnitude, self.mag_error, self.zeropoint)
          
        
    @classmethod
    def from_dict(cls, alert_dict):
        """Filters out unused attributes.
        """
        cls_fields = {field for field in signature(cls).parameters}
        alert_dict_filtered = {k: alert_dict[k] for k in alert_dict if k in cls_fields}

        return Alert(**alert_dict_filtered)
            
            
    @classmethod    
    def fields(cls):
        """Return all alert fields, in desired order.
        """
        return np.array(
            [
                "ID",
                "mjd",
                "ra",
                "dec",
                "band",
                "magnitude",
                "mag_error",
                "flux",
                "flux_error",
                "zeropoint",
            ]
        )
            
            
    

    
    
    