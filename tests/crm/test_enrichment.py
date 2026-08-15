from pathlib import Path

from keprix.crm.enrichment import apply_companies_house_profile, merge_companies_house_profile
from keprix.crm.store import reset_crm_store_for_tests


def test_companies_house_enrichment_is_auditable_and_empty_cell_safe(tmp_path: Path) -> None:
    store = reset_crm_store_for_tests(tmp_path / "enrichment.sqlite")
    lead = store.create_lead("ws_a", name="Existing name", company_name="Known Ltd", locality="Portsmouth")
    profile = {
        "company_number": "01234567",
        "company_name": "Official Ltd",
        "company_status": "active",
        "sic_codes": ["62020"],
        "registered_office_address": {"locality": "London"},
        "officers": [{"name": "Synthetic Officer", "officer_role": "director"}],
    }

    patch = merge_companies_house_profile(lead, profile)
    assert patch["company_number"] == "01234567"
    assert "Official Ltd" not in patch.get("company_name", "")
    assert "locality" not in patch
    assert patch["custom_fields"]["companies_house"]["url"].endswith("/01234567")

    updated = apply_companies_house_profile(store, "ws_a", lead["id"], profile)
    assert updated["company_number"] == "01234567"
    assert updated["company_name"] == "Known Ltd"
    assert updated["custom_fields"]["companies_house"]["officers"][0]["name"] == "Synthetic Officer"
