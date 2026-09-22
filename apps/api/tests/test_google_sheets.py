import uuid

from app.services.google_sheets import (
    SheetLead,
    _formatting_requests,
    _hyperlink_requests,
    _sheet_rows,
)


def test_google_sheet_payload_uses_dynamic_campaign_title() -> None:
    lead = SheetLead(
        priority=1,
        company_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        name="Example Restaurant",
        phone="0550 00 00 00",
        email="Non trouve",
        maps_url="https://www.google.com/maps/search/?api=1&query=Example",
        location="Ain Beida, Algeria",
        problem="No verified first-party website.",
        solution="Create a landing page.",
        status="READY_TO_CONTACT",
    )

    prospecting_rows, source_rows = _sheet_rows(
        [lead], "Prospection restaurants - Ain Beida"
    )
    requests = _formatting_requests(
        prospecting_sheet_id=123,
        sources_sheet_id=456,
        lead_count=1,
        summary_row_index=8,
    )

    assert prospecting_rows[0][0] == (
        "Prospection restaurants - Ain Beida - export automatique AI Opportunity Hunter"
    )
    assert prospecting_rows[2][0] == "#"
    assert prospecting_rows[2][1] == "Nom"
    assert prospecting_rows[3][1] == "Example Restaurant"
    assert prospecting_rows[3][2] == "0550 00 00 00"
    assert prospecting_rows[3][4] == "Ouvrir Maps"
    assert source_rows[2][4] == "Ouvrir Maps"
    assert any("setBasicFilter" in request for request in requests)
    assert any("setDataValidation" in request for request in requests)
    link_requests = _hyperlink_requests(
        prospecting_sheet_id=123,
        sources_sheet_id=456,
        leads=[lead],
    )
    assert len(link_requests) == 2
    assert "link" in str(link_requests[0])
