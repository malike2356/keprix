from keprix.security.scout_standing_orders import set_standing_order


def test_standing_orders_are_off_until_enabled():
    assert set_standing_order("posture", enabled=False)["enabled"] is False
