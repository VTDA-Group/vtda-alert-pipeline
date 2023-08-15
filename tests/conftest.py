import os
import os.path

import pytest
from jax import random
import numpy as np

from 


TEST_DIR = os.path.dirname(__file__)
DATA_DIR_NAME = "data"

@pytest.fixture
def test_data_dir():
    return os.path.join(TEST_DIR, DATA_DIR_NAME)


@pytest.fixture
def test_alert_dict():
    return {
        "ID": "test",
        "mjd": 0.0,
        "ra": 60.0,
        "dec": 60.0,
        "band": "r",
        "magnitude": 19.0,
        "mag_error": 1.0,
        "zeropoint": 26.3,
    }
