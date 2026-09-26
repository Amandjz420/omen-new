# Billing

See [the architecture guide](../../../migration-required/app-reference/DJANGO_APP_ARCHITECTURE.md) for boundaries and the stable database-label policy.

Models defined here:

- `ChargeType`
- `ValuationCharge`
- `Invoice`
- `InvoiceLine`
- `Receipt`
- `ReceiptAllocation`
- `InvoiceFollowUp`
- `IssuerAccount`
- `FeeRule`
- `CreditNote`

Existing models retain the `target_core` migration label. Do not rename it as part of routine maintenance.
