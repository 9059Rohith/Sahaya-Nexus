# API

FastAPI publishes live OpenAPI documentation at `/docs`. All application routes use `/api/v1`.

| Area | Main routes |
| --- | --- |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET/PATCH/DELETE /auth/me`, `POST /auth/volunteer/apply` |
| Interpretation | `POST /requests/interpret`, `POST /speech/transcribe` |
| Requests | `GET/POST /requests`, `GET /requests/{id}`, `POST /requests/{id}/cancel`, `/feedback`, `/outcome/confirm` |
| Similar reports | `POST /requests/duplicates`, `POST /requests/{id}/duplicates/{existing_id}/confirm` |
| Evidence | `POST /requests/{id}/evidence`, `GET /requests/{id}/evidence/{evidence_id}` |
| Organizations | `GET/POST /organizations`, `GET /organizations/mine`, `/organizations/saved`, `POST/DELETE /organizations/{id}/save`, `GET/POST /organizations/{id}/resources`, `GET /organizations/{id}/performance` |
| Resources | `GET /resources`, `PATCH /resources/{id}` |
| Volunteers | `GET /volunteers/opportunities`, `POST /volunteers/opportunities/{id}/interest`, `GET /admin/requests/{id}/interests` |
| Responder | `GET /assignments/mine`, `POST /assignments/{id}/accept`, `/start`, `/arrive`, `/complete` |
| Staff | `GET /admin/queue`, `/admin/escalations`, `/admin/organizations`, `/admin/volunteers`, `/admin/audit`, `/admin/analytics`, `/admin/health`, `/admin/reports/abuse` |
| Lifecycle | `POST /admin/requests/{id}/transition`, `/verify`, `/priority`, `/assign`, `/record-impact`, `/follow-up` |
| Reviews and policy | `POST /admin/organizations/{id}/verify`, `/admin/volunteers/{id}/verify`; `GET/POST /admin/matching-settings`, `GET/PUT /admin/config` |
| Discovery | `GET /search`, `/public/issues`, `/public/summary`, `/public/impact-map`, `/impact`, `/config`, `/health` |
| Trust and notices | `GET /notifications`, `POST /notifications/{id}/read`, `POST /reports/abuse`, `POST /admin/reports/abuse/{id}/resolve` |

Calling FastAPI directly requires a bearer token for protected routes. The browser instead uses the same-origin Next.js proxy and HTTP-only cookie. Mutating proxy requests require a same-origin browser context. Public impact reports only verified, operator-recorded outcomes. The public issue explorer only returns verified community/accessibility reports whose owner opted in, with rounded coordinates and no original description.

Errors use `{ "error": { "code": "...", "message": "..." } }`; validation errors also include `details`. Rate limits use `RATE_LIMITED` with `Retry-After`, which the browser proxy forwards. The Docker stack shares mutation limits through Redis. If that limiter is unavailable, writes return 503 with a retry hint. Request, public issue, organization, resource and staff queue lists have page controls. Requests and staff queue support category, urgency and sort filters; organizations support search and sort; resources support category, search and sort. The API is the source of truth for permissions, lifecycle and matching eligibility.

`GET /health` reports the database and limiter state. It returns 503 with `status: degraded` when the database or configured shared limiter is unavailable. `GET /admin/health` shows the same limiter mode to authorized staff.

`POST /requests` accepts an optional UUID `client_submission_id`. Repeating the same payload and ID for the same account returns the existing request without another timeline event. Reusing that ID with different content returns 409. The browser uses this when a reviewed request is saved on the device after a connection failure; sending it later requires an explicit click.

`GET /requests/{id}/messages?page=1` returns the latest 50 participant messages in chronological display order. `POST /requests/{id}/messages` accepts `{ "body": "..." }` and notifies the requester or assigned responder. The requester, assigned responder and staff can read or send; unrelated accounts receive 404.

`GET /resources/{id}/capacity-history?page=1` returns the latest 50 changes to capacity, workload and availability. Only the organization owner and staff can read this operational history.

Verified organization owners invite registered accounts with `POST /organizations/{id}/members`. The invitee sees `GET /organizations/invitations` and accepts through `POST /organizations/invitations/{invitation_id}/accept`. Owners manage their team through `GET /organizations/{id}/members` and `DELETE /organizations/{id}/members/{user_id}`. Only active memberships grant access to the organization’s resources and assignments. Invitations are in-app only.

`GET /volunteers/opportunities` requires a verified, available volunteer. It supports `category`, `urgency`, `max_distance_km`, `page` and `limit` (up to 100). Only eligible matching requests are counted into each page; private location and free text are never returned in this feed.

`GET/PUT /admin/config` includes `retention_days`: `null` disables automatic closed-request redaction; otherwise an administrator may choose 30–3650 days. Changes are audited. The worker processes at most 50 eligible closed requests per cycle and skips requests with open abuse cases. This policy covers application request content and its private evidence files, not backups or account profiles.
