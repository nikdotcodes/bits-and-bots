"""Legacy SQLite-to-Supabase migration intentionally disabled.

The previous version inserted personal records without idempotency and copied
consent file bytes into a database column. Do not execute the old workflow.
For an existing Supabase deployment, apply the reviewed SQL migration and use
scripts/migrate_consent_files_to_storage.py to move legacy consent scans.
A full historical data migration should be planned against a verified,
redacted schema/data export and tested against a separate Supabase project.
"""
raise SystemExit(
    "Legacy migrate.py is disabled for safety. See docs/PRODUCTION_DEPLOYMENT.md "
    "and scripts/migrate_consent_files_to_storage.py."
)
