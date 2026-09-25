# Migration Pipeline

See [the architecture guide](../../../database/DJANGO_APP_ARCHITECTURE.md) for boundaries and the stable database-label policy.

Models defined here:

- `ImportBatch`
- `SourceIdentity`
- `MigrationIssue`
- `SourceRow`

Existing models retain the `target_core` migration label. Do not rename it as part of routine maintenance.
