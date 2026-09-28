# Data model

All primary keys are UUID strings. Alembic revisions define these tables:

| Table | Purpose |
| --- | --- |
| `users` | Account, role, volunteer availability, languages, categories, skills, transport and location |
| `organizations` | Owner, service categories/area and staff review state |
| `resources` | Category, capacity/workload, availability window, expiry, service radius and coordinates |
| `requests` | Unified need, status, verification, priority, privacy controls and private location |
| `request_events` | Timestamped lifecycle and responder milestones with actor, reason, notes and confidence |
| `request_evidence` | Authorized file metadata |
| `assignments` | One selected verified responder/resource per request |
| `outcomes` | Responder report, citizen confirmation and optional measured units |
| `audit_logs` | Staff decisions and other application mutations |
| `matching_settings` | Administrator-configured matching weights |
| `notifications` | Recipient-scoped in-app status and assignment notices |
| `outcome_feedback` | Citizen Yes/No/Partially result confirmation |
| `duplicate_links` | Citizen-confirmed same-issue relationship |
| `saved_organizations` | Personal verified-organization bookmarks |
| `volunteer_interests` | Verified volunteers' availability signals on eligible requests |
| `abuse_reports` | Safety/fraud reports and staff resolution |
| `platform_settings` | Audited feature flags, pilot rules, thresholds and verification policy |

Impact totals query only requests at `IMPACT_RECORDED` joined to outcomes. No independent counter or seeded number can drift away from confirmed records. `details` is a bounded extension field for domain-specific submission fields such as food safe-until and blood facility name.

PostgreSQL installations with PostGIS have geometry point columns, update triggers and GiST indexes on users, resources and requests. SQLite does not have these columns; application distance calculation remains available for local development. All normal records originate from user or operator actions. The internal automation account is created only when it must record an expiry or escalation.
