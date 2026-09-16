# Deployment information supplied by the owner

Received during the migration on 16 September 2026. Credentials supplied in chat are intentionally not copied into project files.

| Schema | Reported production purpose | Migration boundary |
|---|---|---|
| ebioserver | ESSL attendance devices; used by iclock WAR | Preserve device ingestion contract and attendance history; iclock is an additional deployment dependency |
| lead_mngt | Lead application | Full lead, valuation, work-order, billing, collection and reporting data |
| smldb | Email and SMS logs | Preserve historical logs; services reportedly not currently configured, runtime verification pending |
| uam_user | UAM / HRMS | Identity, HR, payroll-related data and database routines |
| uam_user_uat | UAM / HRMS UAT | Separate test dataset, never merge IDs with main schema |
| lead_mngt_uat | Lead UAT | Separate test dataset |
| smldb_uat | Email / SMS log UAT | Separate test dataset |

## Files outside the database

- Lead application: deployment note says “S# Server.” The source includes `AmazonS3CientUtility.java` and `FileUploadUtility.java`, establishing an S3 integration in code. Actual bucket, region, runtime configuration and completeness of stored files remain to be verified.
- UAM / HRMS: deployment note identifies `/opt/WebServer/ProjectUpload/UAMUpload/` as its local upload directory. Its contents have not been supplied or migrated.
- Preserve each original upload ID, storage key/path, filename and content type. Copy file bytes separately and reconcile existence, size and checksums before changing document links.
- Do not infer that a restored SQL upload row means its associated document has been migrated.
- Source for iclock WAR and its device API contract has not yet been identified among the supplied seven Java projects. Preserve the deployed device service until its replacement is validated.

## Access and verification

The owner supplied production server and database credentials as context. No production connection or write has been performed. Current work uses the local SQL dump and an isolated local container with independently generated credentials. Confirm the intended read-only production inspection scope before using production access.

## Cutover dependencies

Database reconciliation, document storage migration, iclock/device integration, source configuration, scheduled jobs, optional messaging configuration, and role/permission parity must all be tracked independently. The local database baseline does not establish full application parity.
