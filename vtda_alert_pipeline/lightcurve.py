import numpy as np
import dataclasses
import os
from dataclasses import dataclass, field
from alert import Alert


@dataclass
class LightCurve:
    """Class to store information about each light curve.
    """
    
    ID: str
    alerts: pd.DataFrame = field(default_factory=pd.DataFrame)
    properties: Dict = field(default_factory=Dict)
    
    
    def __post_init__(self):
        """Additional alerts formatting after initialization.
        """
        included_cols = self.alerts.columns
        all_cols = Alert.fields
        
        num_entries = len(self.alerts)
        for field in all_cols:
            if field not in included_cols:
                self.alert[field] = np.nan
                
        self.alerts = self.alerts[all_cols] # reorder
            
        self.alerts.sort_values(by=['mjd'], in_place=True)

        
    def add_alert(alert, assume_latest=False):
        """Add alert such that MJD order is maintained.
        If assume_latest, does not check time values and inserts
        array at end of time series (risky!)
        """
        assert type(alert) == Alert
        
        if assume_latest: # assume mjd is latest in timeseries
            self.alerts.iloc[-1] = vars(alert)
        
        else:
            # insert alert into row according to ordered time values
            # assumes existing df in proper time order
            prev_row_idx = self.alerts[self.alerts.mjd <= alert.mjd].idxmax()

            self.alerts.iloc[prev_row_idx+1] = alert.dict

            
    def add_property(self, prop_key, prop_value, overwrite=True):
        """Add property from filter.
        """
        if overwrite or (prop_key not in self.properties):
            self.properties[prop_key] = prop_value
            
        
    @property
    def timeseries(self, cols=None):
        """Return time series of alerts,
        as a DataFrame.
        """
        if cols is None:
            return self.alerts
        
        return self.alerts[cols]
        
        
        
        
        
        
    
    
    
    
    