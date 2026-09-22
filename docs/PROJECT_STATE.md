# Project State

## Current milestone

Fixture-backed MVP vertical slice complete. Neon PostgreSQL and the Google Workspace project workbook are connected.

## Execution architecture

`python_langgraph`, direct execution. FastAPI submits a LangGraph campaign run; thin graph nodes call Python domain services. PostgreSQL is the production source of truth. Celery/Redis remains intentionally deferred until measured scale requires it.

## Working features

- Workspace bootstrap and default service catalog.
- Campaign creation, listing, retrieval, start, execution status, and safe queued cancellation.
- Fixture discovery of ten representative companies.
- Google Places Text Search adapter with field masks and provider identifiers.
- Company normalization, provider/domain deduplication, contacts, locations, and digital assets.
- Safe HTTP crawler utilities with SSRF, redirect, size, content-type, and timeout controls.
- Evidence persistence with provenance, confidence, retention class, and content hashes.
- Deterministic grounded problem analysis plus optional DeepSeek V4 Pro structured analysis.
- Deterministic service compatibility, sales angle generation, and transparent weighted scoring.
- Ranked leads, detailed evidence briefs, limitations, and eight-dimension score breakdowns.
- LangGraph campaign graph, stable `campaign:{uuid}` thread identity, checkpoint test, and idempotent job execution.
- Idempotent CSV export and production Google Sheets exporter with batched writes, frozen headers, filters, formatting, score highlighting, and Drive sharing.
- Responsive Next.js dashboard for campaign creation, progress, lead review, and exports.
- CI workflow for Python and Next.js gates.

## Verification

- 15 backend tests pass, including the fixture campaign E2E and idempotent export test.
- Ruff format/lint and strict mypy pass.
- Both Alembic migrations compile for PostgreSQL, apply successfully to the local SQLite demo database, and are applied at Neon revision `20260705_0002`.
- Next.js lint and production build pass on Node 24.
- Browser E2E passed: 10 discovered, 8 qualified, 7 hot, opportunity drawer rendered, no browser console errors.
- OpenRouter/DeepSeek V4 Pro strict-schema smoke test passed earlier in this workspace.
- Neon-to-Google MCP demo passed: 10 fixture companies discovered, 8 qualified leads persisted, and 7 hot leads written to the connected workbook.
- Live Oum El Bouaghi medical scan passed: 5 Google Places candidates discovered, 5 analyzed, 5 qualified after controlled-taxonomy repair, persisted in Neon, and exported to Google Sheets. The run used two Places requests total (the first execution timed out during sequential LLM analysis) and at most one LLM analysis on the successful retry.
- Live API verification passed against Neon (`health=200`, campaign `READY_FOR_REVIEW`, five leads). Neon free-tier cold start was observed; warm lead-list latency fell to approximately 0.9 seconds after consolidating N+1 reads into one query.

## Real integrations

- OpenRouter adapter is implemented and credential/model routing was live-smoke-tested.
- Google Places (New) authentication and billing were live-verified with one minimal-field, one-result Text Search request on 2026-07-06; no campaign scan was run.
- Google Workspace MCP authentication is verified for `islambenaboud007@gmail.com`.
- Project workbook created and read/write verified: `1VJOvLKnz91_muyTEHHtskZZkexgQJ_sfldaavmr5ijw`.
- Google Sheets Python adapter remains available for unattended runtime exports; MCP is used for operator-managed workbook access.

## External blockers

- Unattended Python Google Sheets export requires `GOOGLE_SERVICE_ACCOUNT_JSON`; interactive/operator workbook management is already available through Google MCP.

## Required environment variables for production

- `DATABASE_URL` (configured for Neon; secret stored only in `.env`)
- `LLM_API_KEY`
- `GOOGLE_MAPS_API_KEY`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEETS_USER_EMAIL`

## Security notes

- Secrets are server-only and `.env` is ignored.
- Supabase-facing tables enable RLS without public policies; browser access goes through FastAPI.
- Crawled content is treated as untrusted data and cannot instruct the LLM.
- Outreach is not automated.

## Next recommended tasks

1. Monitor Google Places cost per campaign before increasing discovery limits.
2. Add authentication/workspace membership before public multi-user deployment.
3. Add Celery only after concurrency or campaign-duration measurements justify it.
