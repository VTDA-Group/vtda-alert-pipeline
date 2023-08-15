import abc

class Filter(abc.ABC):
    """Abstract class for filter."""
    
    @abc.abstractmethod
    def setup(self):
        """Setup is run once for all light curves."""
        
    
    @abc.abstractmethod
    def run(self, lc):
        """Run for each individual light curve."""
        

