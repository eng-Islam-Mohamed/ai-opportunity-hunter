import pytest
from app.services.crawling import parse_observations
from app.services.normalization import canonicalize_url, domain_from_url, normalize_name
from app.services.url_safety import UnsafeUrlError, validate_public_url


def test_normalization() -> None:
    assert normalize_name("  Marina & Smile—Dental! ") == "marina smile dental"
    assert canonicalize_url("Example.COM/contact/") == "https://example.com/contact"
    assert domain_from_url("https://www.Example.com/path") == "example.com"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "http://localhost/",
    ],
)
def test_ssrf_destinations_are_blocked(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url, resolve_dns=False)


def test_conversion_observation_parser() -> None:
    result = parse_observations(
        "https://clinic.example",
        """
        <html><head><title>Clinic</title></head><body>
          <a href="/book-appointment">Book</a>
          <a href="https://wa.me/971500000000">WhatsApp</a>
          <form action="/contact"></form>
          <script src="https://client.crisp.chat/widget.js"></script>
        </body></html>
        """,
    )
    assert result.booking_link_detected
    assert result.whatsapp_link_detected
    assert result.contact_form_detected
    assert result.chat_widget_detected
