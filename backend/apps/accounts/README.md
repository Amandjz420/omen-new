# Accounts

See [the architecture guide](../../../database/DJANGO_APP_ARCHITECTURE.md) for boundaries and the stable database-label policy.

Models defined here:

- `LegacyProject`
- `RoleDefinition`
- `LegacyAccount`
- `RoleAssignment`
- `LoginEvent`

Existing models retain the `target_core` migration label. Do not rename it as part of routine maintenance.
