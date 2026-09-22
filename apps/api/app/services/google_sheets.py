from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.opportunity import ContactPoint, ExportJob, ProviderEntity
from app.schemas.opportunity import ExportRead, LeadListItem
from app.services.leads import list_campaign_leads

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@dataclass(frozen=True)
class SheetLead:
    priority: int
    company_id: uuid.UUID
    name: str
    phone: str
    email: str
    maps_url: str
    location: str
    problem: str
    solution: str
    status: str


def _rgb(red: int, green: int, blue: int) -> dict[str, float]:
    return {"red": red / 255, "green": green / 255, "blue": blue / 255}


def _maps_url(name: str, location: str, place_id: str | None) -> str:
    query = quote_plus(f"{name} {location}".strip())
    if place_id:
        return (
            "https://www.google.com/maps/search/"
            f"?api=1&query={query}&query_place_id={quote_plus(place_id)}"
        )
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def _problem_fr(problem: str | None) -> str:
    if not problem:
        return "Problème digital à vérifier manuellement."
    normalized = problem.lower()
    if "no verified first-party website" in normalized or "website" in normalized:
        return (
            "Pas de site officiel vérifié; pas de prise de rendez-vous digitale détectée; "
            "contact digital faible."
        )
    return problem


def _programming_solution(solution: str | None) -> str:
    if not solution:
        return "Créer un outil simple de contact, suivi et conversion adapté au cabinet."
    normalized = solution.lower()
    if "website" in normalized:
        return (
            "Créer une landing page + bouton appel/Maps/WhatsApp + formulaire RDV "
            "+ mini CRM de suivi."
        )
    if "crm" in normalized:
        return "Créer un mini CRM de suivi des demandes, relances et rendez-vous."
    if "whatsapp" in normalized or "booking" in normalized:
        return "Créer un agent WhatsApp de prise de RDV + qualification + rappels."
    return solution


def _campaign_sheet_title(campaign: Campaign) -> str:
    query = campaign.target.get("query") if isinstance(campaign.target, dict) else None
    location = campaign.target.get("location_text") if isinstance(campaign.target, dict) else None
    parts = [str(part).strip() for part in [query, location] if str(part or "").strip()]
    if parts:
        return f"Prospection {' - '.join(parts)}"
    return f"Prospection {campaign.name}"


def _sheet_rows(leads: list[SheetLead], title: str) -> tuple[list[list[object]], list[list[object]]]:
    prospecting_rows: list[list[object]] = [
        [f"{title} - export automatique AI Opportunity Hunter"],
        [],
        [
            "#",
            "Nom",
            "Téléphone",
            "Email",
            "Lien Maps",
            "Problème détecté",
            "Solution programmation",
            "Statut",
            "Notes",
        ],
    ]
    for lead in leads:
        prospecting_rows.append(
            [
                lead.priority,
                lead.name,
                lead.phone,
                lead.email,
                "Ouvrir Maps" if lead.maps_url else "",
                lead.problem,
                lead.solution,
                "À contacter",
                "Appeler puis noter la réponse",
            ]
        )
    prospecting_rows.extend([[], [], [], []])
    with_phone = sum(1 for lead in leads if lead.phone != "Non trouvé")
    prospecting_rows.append(
        [
            "Total leads qualifiés",
            "",
            len(leads),
            f"Avec téléphone: {with_phone} / {len(leads)} — Emails vérifiés: "
            f"{sum(1 for lead in leads if '@' in lead.email)}",
        ]
    )

    source_rows: list[list[object]] = [
        ["Sources Google Places et limites"],
        ["Nom", "Téléphone", "Email", "Adresse", "Lien Maps", "Limite"],
    ]
    source_rows.extend(
        [
            lead.name,
            lead.phone,
            lead.email,
            lead.location,
            "Ouvrir Maps" if lead.maps_url else "",
            "Email non vérifié; site web non retourné par Google Places quand absent.",
        ]
        for lead in leads
    )
    return prospecting_rows, source_rows


def _hyperlink_requests(
    *,
    prospecting_sheet_id: int,
    sources_sheet_id: int,
    leads: list[SheetLead],
) -> list[dict[str, object]]:
    requests: list[dict[str, object]] = []
    for index, lead in enumerate(leads):
        if not lead.maps_url:
            continue
        prospecting_row = 3 + index
        source_row = 2 + index
        for sheet_id, row, column in [
            (prospecting_sheet_id, prospecting_row, 4),
            (sources_sheet_id, source_row, 4),
        ]:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row,
                            "endRowIndex": row + 1,
                            "startColumnIndex": column,
                            "endColumnIndex": column + 1,
                        },
                        "cell": {
                            "userEnteredValue": {"stringValue": "Ouvrir Maps"},
                            "userEnteredFormat": {
                                "textFormat": {
                                    "foregroundColor": _rgb(17, 85, 204),
                                    "underline": True,
                                    "link": {"uri": lead.maps_url},
                                },
                                "horizontalAlignment": "CENTER",
                            },
                        },
                        "fields": "userEnteredValue,userEnteredFormat(textFormat,horizontalAlignment)",
                    }
                }
            )
    return requests


def _formatting_requests(
    *,
    prospecting_sheet_id: int,
    sources_sheet_id: int,
    lead_count: int,
    summary_row_index: int,
) -> list[dict[str, object]]:
    data_start = 3
    data_end = data_start + lead_count
    requests: list[dict[str, object]] = [
        {
            "mergeCells": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "mergeType": "MERGE_ALL",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(81, 69, 229),
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "foregroundColor": _rgb(255, 255, 255),
                            "bold": True,
                            "fontSize": 16,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": 2,
                    "endRowIndex": 3,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(15, 118, 110),
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "foregroundColor": _rgb(255, 255, 255),
                            "bold": True,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": data_start,
                    "endRowIndex": data_end,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(234, 241, 255),
                        "wrapStrategy": "WRAP",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,wrapStrategy,verticalAlignment)",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": data_start,
                    "endRowIndex": data_end,
                    "startColumnIndex": 2,
                    "endColumnIndex": 3,
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "textFormat": {"bold": True, "foregroundColor": _rgb(0, 128, 96)},
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": data_start,
                    "endRowIndex": data_end,
                    "startColumnIndex": 3,
                    "endColumnIndex": 4,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(254, 226, 226),
                        "textFormat": {"bold": True, "foregroundColor": _rgb(220, 38, 38)},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": data_start,
                    "endRowIndex": data_end,
                    "startColumnIndex": 7,
                    "endColumnIndex": 8,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(254, 243, 199),
                        "horizontalAlignment": "CENTER",
                        "textFormat": {"bold": True, "foregroundColor": _rgb(180, 83, 9)},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)",
            }
        },
        {
            "setDataValidation": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": data_start,
                    "endRowIndex": max(data_end + 20, data_start + 20),
                    "startColumnIndex": 7,
                    "endColumnIndex": 8,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [
                            {"userEnteredValue": value}
                            for value in [
                                "À contacter",
                                "Contacté",
                                "Intéressé",
                                "Pas intéressé",
                                "Relance",
                                "Client potentiel",
                            ]
                        ],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": prospecting_sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": max(data_end, 3),
                        "startColumnIndex": 0,
                        "endColumnIndex": 9,
                    }
                }
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": prospecting_sheet_id,
                    "gridProperties": {"frozenRowCount": 3, "hideGridlines": True},
                },
                "fields": "gridProperties(frozenRowCount,hideGridlines)",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 9,
                },
                "properties": {"pixelSize": 130},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": data_start,
                    "endIndex": data_end,
                },
                "properties": {"pixelSize": 72},
                "fields": "pixelSize",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": prospecting_sheet_id,
                    "startRowIndex": summary_row_index,
                    "endRowIndex": summary_row_index + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(254, 243, 199),
                        "textFormat": {"bold": True},
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)",
            }
        },
        {
            "mergeCells": {
                "range": {
                    "sheetId": sources_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 6,
                },
                "mergeType": "MERGE_ALL",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sources_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 2,
                    "startColumnIndex": 0,
                    "endColumnIndex": 6,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": _rgb(15, 118, 110),
                        "textFormat": {
                            "foregroundColor": _rgb(255, 255, 255),
                            "bold": True,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sources_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 6,
                }
            }
        },
    ]
    for column, width in {
        0: 45,
        1: 335,
        2: 145,
        3: 170,
        4: 125,
        5: 350,
        6: 405,
        7: 150,
        8: 275,
    }.items():
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": prospecting_sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column,
                        "endIndex": column + 1,
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            }
        )
    return requests


class GoogleSheetsExporter:
    def __init__(
        self,
        service_account_json: str | None,
        user_email: str | None = None,
        oauth_client_secrets_file: str | None = None,
        oauth_token_file: str | None = None,
        oauth_client_secrets_json: str | None = None,
        oauth_token_json: str | None = None,
    ) -> None:
        self._credentials_info = json.loads(service_account_json) if service_account_json else None
        self._user_email = user_email
        self._oauth_client_secrets_file = oauth_client_secrets_file
        self._oauth_token_file = oauth_token_file or ".secrets/google-oauth-token.json"
        self._oauth_client_secrets_json = oauth_client_secrets_json
        self._oauth_token_json = oauth_token_json

    def _credentials(self) -> Any:
        if self._credentials_info is not None:
            return service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
                self._credentials_info, scopes=SCOPES
            )

        if self._oauth_token_json:
            credentials = Credentials.from_authorized_user_info(
                json.loads(self._oauth_token_json), SCOPES
            )
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())  # type: ignore[no-untyped-call]
            if credentials.valid:
                return credentials

        if self._oauth_client_secrets_file is None and self._oauth_client_secrets_json is None:
            raise ValueError(
                "Google Sheets export is not configured. Provide service account JSON or OAuth client secrets file."
            )

        if self._oauth_client_secrets_file is None:
            raise ValueError(
                "GOOGLE_OAUTH_TOKEN_JSON must be set for cloud export. Interactive OAuth is only supported locally."
            )
        client_secrets_path = Path(self._oauth_client_secrets_file)
        if not client_secrets_path.is_file():
            raise ValueError(
                "Google OAuth client file is missing. Add the downloaded OAuth desktop-client JSON "
                "file and update GOOGLE_OAUTH_CLIENT_SECRETS_FILE."
            )

        token_path = Path(self._oauth_token_file)
        credentials: Credentials | None = None
        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
                str(token_path), SCOPES
            )
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())  # type: ignore[no-untyped-call]
            except RefreshError:
                # A revoked or expired refresh token must fall back to the normal
                # interactive OAuth flow instead of making the export endpoint fail.
                credentials = None
        if credentials is None or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path), SCOPES
            )
            credentials = flow.run_local_server(
                port=0,
                open_browser=True,
                authorization_prompt_message=(
                    "Open this URL to authorize Google Sheets export: {url}"
                ),
            )
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def _services(self) -> tuple[Any, Any]:
        credentials = self._credentials()
        return (
            build("sheets", "v4", credentials=credentials, cache_discovery=False),
            build("drive", "v3", credentials=credentials, cache_discovery=False),
        )

    def _export_sync(self, title: str, leads: list[SheetLead]) -> tuple[str, str]:
        sheets, drive = self._services()
        workbook = (
            sheets.spreadsheets()
            .create(
                body={
                    "properties": {"title": title},
                    "sheets": [
                        {"properties": {"title": "Prospection"}},
                        {"properties": {"title": "Sources"}},
                    ],
                },
                fields="spreadsheetId,spreadsheetUrl,sheets.properties",
            )
            .execute()
        )
        spreadsheet_id = workbook["spreadsheetId"]
        sheet_ids = {
            item["properties"]["title"]: item["properties"]["sheetId"]
            for item in workbook["sheets"]
        }
        prospecting_rows, source_rows = _sheet_rows(leads, title)
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": "'Prospection'!A1", "values": prospecting_rows},
                    {"range": "'Sources'!A1", "values": source_rows},
                ],
            },
        ).execute()
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": _formatting_requests(
                    prospecting_sheet_id=sheet_ids["Prospection"],
                    sources_sheet_id=sheet_ids["Sources"],
                    lead_count=len(leads),
                    summary_row_index=len(leads) + 7,
                )
                + _hyperlink_requests(
                    prospecting_sheet_id=sheet_ids["Prospection"],
                    sources_sheet_id=sheet_ids["Sources"],
                    leads=leads,
                )
            },
        ).execute()
        if self._user_email:
            drive.permissions().create(
                fileId=spreadsheet_id,
                body={"type": "user", "role": "writer", "emailAddress": self._user_email},
                sendNotificationEmail=False,
            ).execute()
        return spreadsheet_id, workbook["spreadsheetUrl"]

    async def export(self, title: str, leads: list[SheetLead]) -> tuple[str, str]:
        return await asyncio.to_thread(self._export_sync, title, leads)


async def _build_sheet_leads(
    session: AsyncSession, leads: list[LeadListItem]
) -> list[SheetLead]:
    provider_rows = (
        await session.execute(
            select(ProviderEntity.company_id, ProviderEntity.provider_entity_id).where(
                ProviderEntity.company_id.in_([lead.company_id for lead in leads])
            )
        )
    ).all()
    email_rows = (
        await session.execute(
            select(ContactPoint.company_id, ContactPoint.value).where(
                ContactPoint.company_id.in_([lead.company_id for lead in leads]),
                ContactPoint.kind == "email",
            )
        )
    ).all()
    place_ids = {company_id: place_id for company_id, place_id in provider_rows}
    emails = {company_id: value for company_id, value in email_rows}
    return [
        SheetLead(
            priority=index,
            company_id=lead.company_id,
            name=lead.company_name,
            phone=lead.phone or "Non trouvé",
            email=emails.get(lead.company_id, "Non trouvé"),
            maps_url=_maps_url(lead.company_name, lead.location or "", place_ids.get(lead.company_id)),
            location=lead.location or "",
            problem=_problem_fr(lead.main_problem),
            solution=_programming_solution(lead.recommended_solution),
            status=lead.status,
        )
        for index, lead in enumerate(leads, start=1)
    ]


async def export_campaign_google_sheets(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    service_account_json: str | None,
    user_email: str | None,
    oauth_client_secrets_file: str | None = None,
    oauth_token_file: str | None = None,
    oauth_client_secrets_json: str | None = None,
    oauth_token_json: str | None = None,
) -> ExportRead:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise ValueError("Campaign not found")
    job = await session.scalar(
        select(ExportJob).where(
            ExportJob.campaign_id == campaign_id,
            ExportJob.provider == "google_sheets",
        )
    )
    if job is None:
        job = ExportJob(
            campaign_id=campaign_id,
            provider="google_sheets",
            status="RUNNING",
        )
        session.add(job)
        await session.flush()
    else:
        job.status = "RUNNING"
    leads = await list_campaign_leads(session, campaign_id)
    sheet_leads = await _build_sheet_leads(session, leads)
    external_id, external_url = await GoogleSheetsExporter(
        service_account_json,
        user_email,
        oauth_client_secrets_file,
        oauth_token_file,
        oauth_client_secrets_json,
        oauth_token_json,
    ).export(_campaign_sheet_title(campaign), sheet_leads)
    job.status = "COMPLETED"
    job.external_id = external_id
    job.external_url = external_url
    job.row_count = len(leads)
    await session.commit()
    return ExportRead(
        id=job.id,
        campaign_id=job.campaign_id,
        provider=job.provider,
        status=job.status,
        external_url=job.external_url,
        row_count=job.row_count,
    )


