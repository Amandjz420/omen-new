# database

Only `.local/` remains here: local, git-ignored configuration the application
reads, namely the PostgreSQL connection (`postgres.json`), the legacy source
connection for the importer (`connection.json`) and generated admin credentials.
Keep it private (mode 700).

The migration documents, mapping data, tools and import reports that used to live
here are in [`../migration-required/`](../migration-required/README.md).
