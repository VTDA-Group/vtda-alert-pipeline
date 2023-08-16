from vtda_alert_pipeline.alert import Alert


def test_alert_create(test_alert_dict):
    """Test creation of Alert from dictionary and individual
    attributes.
    """
    alert1 = Alert.from_dict(test_alert_dict)
    assert alert1.mjd == 0.0
    # TODO: add flux calculation assertion
    
    alert2 = Alert(**test_alert_dict)
    assert alert2.mjd == 0.0
    
    # test dictionary with extra kwargs
    extended_dict = test_alert_dict
    extended_dict['extra_kwarg'] = 0.0
    alert3 = Alert.from_dict(extended_dict)
    assert alert3.mjd == 0.0
    