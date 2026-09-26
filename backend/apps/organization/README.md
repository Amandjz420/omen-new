# Organization

See [the architecture guide](../../../migration-required/app-reference/DJANGO_APP_ARCHITECTURE.md) for boundaries and the stable database-label policy.

Models defined here:

- `Employee`
- `SalaryBaseline`
- `SalaryBaselineComponent`
- `SalaryResult`
- `LeaveOpeningBalance`
- `LeadDivision`
- `LeadSubdivision`
- `EmployeeTarget`
- `EmployeeAssignmentRule`

Existing models retain the `target_core` migration label. Do not rename it as part of routine maintenance.
