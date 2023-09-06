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

        

