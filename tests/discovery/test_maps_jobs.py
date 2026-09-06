from __future__ import annotations

from keprix.discovery.adapters.google_places import GooglePlacesAdapter
from keprix.discovery.adapters.hunter import HunterAdapter
from keprix.discovery.models import AdapterHealthStatus


def test_maps_adapters_are_disabled_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)

    google = GooglePlacesAdapter().health()
    hunter = HunterAdapter().health()

    assert google.status == AdapterHealthStatus.DISABLED
    assert google.enabled is False
    assert hunter.status == AdapterHealthStatus.DISABLED
    assert hunter.enabled is False


def test_google_places_normalizes_official_payload(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"places":[{"id":"places/1","displayName":{"text":"Example Clinic"},"formattedAddress":"1 Main St","nationalPhoneNumber":"+441234567890","websiteUri":"https://example.test","primaryType":"medical_clinic"}]}'

    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-key")
    monkeypatch.setattr("keprix.discovery.adapters.google_places.urlopen", lambda *args, **kwargs: Response())
    from keprix.discovery.models import DiscoverLimits, DiscoverQuery

    candidates = GooglePlacesAdapter().discover(DiscoverQuery(text="clinic", domain_pack="health_social"), DiscoverLimits(max_results=5))
    assert len(candidates) == 1
    assert candidates[0].company == "Example Clinic"
    assert candidates[0].geo["address"] == "1 Main St"
    assert candidates[0].phones == ["+441234567890"]
    assert candidates[0].source == "google_places"


def test_hunter_miss_does_not_fabricate_email(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"data":{"organization":"Example","emails":[]}}'

    monkeypatch.setenv("HUNTER_API_KEY", "test-key")
    monkeypatch.setattr("keprix.discovery.adapters.hunter.urlopen", lambda *args, **kwargs: Response())
    from keprix.discovery.models import DiscoverLimits, DiscoverQuery

    candidates = HunterAdapter().discover(DiscoverQuery(text="example.test"), DiscoverLimits(max_results=1))
    assert len(candidates) == 1
    assert candidates[0].emails == []
    assert candidates[0].source == "hunter"
