from __future__ import annotations

from app.schemas.campaign import SearchTarget
from app.schemas.opportunity import DiscoveredBusiness


class FixtureDiscoveryProvider:
    async def search(self, target: SearchTarget, *, limit: int) -> list[DiscoveredBusiness]:
        profiles = [
            ("Marina Smile Dental", "marina-smile.example", True, False, True, False, 4.3, 84),
            ("Pearl Dental Care", "pearl-dental.example", False, False, True, False, 4.1, 47),
            ("Harbour Family Clinic", "harbour-family.example", True, True, True, True, 4.7, 191),
            ("Bright Bite Center", "bright-bite.example", False, False, False, False, 3.9, 26),
            ("Ocean Dental Studio", "ocean-dental.example", True, False, True, False, 4.5, 112),
            ("Skyline Orthodontics", "skyline-ortho.example", True, True, True, False, 4.6, 133),
            ("Marina Pearl Dentistry", "marina-pearl.example", False, False, True, False, 4.0, 39),
            ("Blue Wave Dental", "blue-wave.example", True, False, True, True, 4.4, 76),
            ("Palm View Clinic", "palm-view.example", False, False, True, False, 3.8, 18),
            ("Crescent Dental Hub", "crescent-hub.example", True, True, True, True, 4.8, 224),
        ]
        results: list[DiscoveredBusiness] = []
        for index, (name, domain, has_site, booking, whatsapp, chat, rating, reviews) in enumerate(
            profiles
        ):
            website = f"https://{domain}" if has_site else None
            results.append(
                DiscoveredBusiness(
                    provider="fixture",
                    provider_entity_id=f"fixture-{index + 1}",
                    name=name,
                    address=f"Unit {index + 10}, {target.location_text}",
                    city=target.location_text.split(",")[0].strip(),
                    country_code=target.country_code,
                    latitude=25.08 + index / 1000,
                    longitude=55.14 + index / 1000,
                    website=website,
                    phone=f"+97150000{index:04d}",
                    email=f"info@{domain}" if has_site else None,
                    rating=rating,
                    review_count=reviews,
                    signals={
                        "booking_link_detected": booking,
                        "whatsapp_link_detected": whatsapp,
                        "contact_form_detected": has_site,
                        "chat_widget_detected": chat,
                        "mobile_friendly": index % 4 != 3,
                        "performance_score": 42 + index * 5,
                    },
                )
            )
        return results[:limit]
