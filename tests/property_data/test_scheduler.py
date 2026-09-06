from keprix.property_data.scheduler import property_refresh_schedule


def test_property_refresh_schedule_defaults_to_weekly(monkeypatch):
    monkeypatch.delenv("KEPRIX_PROPERTY_DATA_REFRESH_CRON", raising=False)
    monkeypatch.delenv("KEPRIX_PROPERTY_DATA_REFRESH_ENABLED", raising=False)
    schedule = property_refresh_schedule()
    assert schedule["enabled"] is True
    assert schedule["schedule"] == "0 3 * * 0"
    assert schedule["action"]["name"] == "property_data_refresh"
