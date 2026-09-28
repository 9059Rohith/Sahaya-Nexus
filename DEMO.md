# Real-data workflow

No demo seed or fake impact record is provided. To show the system, create accounts owned by the people participating in the demonstration and enter a genuine request. Do not represent a rehearsal request as a real public need.

1. Create the initial admin with `python -m app.cli create-admin` after migrations.
2. A community organization registers and adds a resource with its true capacity. An admin reviews and verifies the organization.
3. A citizen describes a real need. They inspect and edit the local interpretation, add location and domain-specific fields, then submit.
4. An operator moves through understanding, validation and verification, records the reason, prioritizes, compares eligible matches and assigns one.
5. The responder accepts, starts, marks arrival, performs the work and records what happened with any measured units.
6. The citizen answers Yes, No or Partially. Yes lets the operator record impact; No or Partially escalates the need and the operator can open a linked follow-up. Only verified, recorded outcomes increase the Impact page.

For a **test environment only**, the pytest integration test runs the same food-rescue path against an isolated in-memory database. It never seeds the application database.
