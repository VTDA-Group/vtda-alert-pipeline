from ..filter_base import Filter


class TestFilter(Filter):
    """Test filter """

    def __init__(self):
        self.name = "Test"

    def setup(self):
        """Setup is run once for all light curves."""
        pass

    def run(self, target):
        """Run for each individual light curve."""
        target.save(extras={'test_field': 0})
