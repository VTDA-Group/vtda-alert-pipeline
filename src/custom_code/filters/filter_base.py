import abc
import subprocess

class Filter(abc.ABC):
    """Abstract class for filter."""
    
    @abc.abstractmethod
    def __init__(self):
        self.name = "base"
        
    @abc.abstractmethod
    def setup(self):
        """Setup is run once for all light curves."""
        pass
    
    @abc.abstractmethod
    def run(self, target):
        """Run for each individual light curve."""
        pass
        
    @classmethod
    def get_all_filters():
        """Get list of all filters"""
        filters = []
        filter_fn_list = glob.glob("./filters/*.py")
        for filter_fn in filter_fn_list:
            filter_obj = subprocess.run(["python", filter_fn]) 
            filters.append(filter_obj)
        return filters

        

