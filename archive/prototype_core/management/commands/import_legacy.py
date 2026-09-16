import hashlib
import json
from datetime import date
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Bank, Office, Contact, Lead, Case, SourceRecord, ImportBatch

KEYS = {'Banks': 'bank_id', 'Client Offices': 'client_id', 'Contacts': 'orderer_reg_id',
        'Leads': 'lead_id', 'Cases': 'client_customer_id', 'Linked Bank Branches': 'branch_id',
        'Employee References': 'emp_id', 'Services': 'service_type_id', 'Service Subtypes': 'service_sub_type_id',
        'Client Types': 'client_type_id', 'Designations': 'client_designation_id', 'Borrower Fees': 'lead_borrower_id',
        'Work Orders': 'lead_order_id', 'Case Order Links': 'valuation_id', 'Lead Services': 'lead_service_id',
        'Invoice Summaries': 'invoice_id'}


def load_rows(path):
    payload = path.read_bytes()
    try:
        books = json.loads(payload)
        sheets = {}
        for book in books:
            for sheet in book['sheets']:
                name = sheet['name']
                if name not in KEYS:
                    continue
                if name in sheets:
                    raise ValueError(f'Duplicate sheet: {name}')
                columns = sheet['columns']
                if len(columns) != len(set(columns)) or KEYS[name] not in columns:
                    raise ValueError(f'Invalid headers: {name}')
                rows = []
                seen = set()
                for values in sheet['rows']:
                    if len(values) != len(columns):
                        raise ValueError(f'Invalid row length: {name}')
                    row = dict(zip(columns, values))
                    key = row[KEYS[name]]
                    if not isinstance(key, str) or not key or key in seen:
                        raise ValueError(f'Missing, non-text or duplicate key: {name}')
                    seen.add(key)
                    rows.append(row)
                sheets[name] = rows
        if set(sheets) != set(KEYS):
            raise ValueError('Missing business sheets: ' + ', '.join(sorted(set(KEYS) - set(sheets))))
        return sheets, hashlib.sha256(payload).hexdigest()
    except (ValueError, KeyError, TypeError) as exc:
        raise CommandError(f'Invalid export: {exc}') from exc


class Command(BaseCommand):
    help = 'Import the JSON projection used to generate the marketing Excel workbooks, atomically and repeatedly.'
    def add_arguments(self, parser):
        parser.add_argument('path', type=Path)
        parser.add_argument('--dry-run', action='store_true', help='Run the full import then roll it back')

    def handle(self, *args, **options):
        sheets, checksum = load_rows(options['path'])
        report = {}
        with transaction.atomic():
            maps = {}
            def linked(model, value, issues, field, required=True):
                if value in (None, '', '0'):
                    if required:
                        issues.append(f'Missing {field}')
                    return None
                found = maps[model].get(str(value))
                if found is None:
                    issues.append(f'Unmatched {field}: {value}')
                return found

            for sheet, model in [('Banks', Bank), ('Client Offices', Office), ('Contacts', Contact), ('Leads', Lead), ('Cases', Case)]:
                existing = {o.source_id: o for o in model.objects.all()}
                created, updated = [], []
                counts = {'inserted': 0, 'updated': 0, 'unchanged': 0, 'rows_with_issues': 0}
                for row in sheets[sheet]:
                    issues = []
                    values = {'raw': row}
                    if model is Bank:
                        values['name'] = row.get('name') or ''
                    elif model is Office:
                        values.update(name=row.get('name') or '', branch=row.get('branch') or '',
                                      bank_id=linked(Bank, row.get('bank_id'), issues, 'bank_id', False))
                    elif model is Contact:
                        values.update(name=row.get('orderer_name') or '', office_id=linked(Office, row.get('client_id'), issues, 'client_id'))
                    elif model is Lead:
                        try:
                            received = date.fromisoformat(str(row.get('lead_date'))[:10])
                            if received.year < 1900:
                                raise ValueError()
                        except ValueError:
                            received = None
                            issues.append('Missing or invalid lead-entry date')
                        values.update(number=row.get('lead_no') or '', office_id=linked(Office, row.get('client_id'), issues, 'client_id'),
                                      contact_id=linked(Contact, row.get('orderer_reg_id'), issues, 'orderer_reg_id', False),
                                      received_date=received, status=str(row.get('lead_status') or ''))
                    else:
                        values.update(lead_id=linked(Lead, row.get('lead_id'), issues, 'lead_id'), service=row.get('service_name') or '',
                                      subtype=row.get('asset_subtype_name_raw') or '', district=row.get('asset_district_name') or '')
                    values['issues'] = issues
                    counts['rows_with_issues'] += bool(issues)
                    key = row[KEYS[sheet]]
                    obj = existing.get(key)
                    if obj is None:
                        created.append(model(source_id=key, **values))
                        counts['inserted'] += 1
                    elif any(getattr(obj, k) != v for k, v in values.items()):
                        for k, v in values.items():
                            setattr(obj, k, v)
                        updated.append(obj)
                        counts['updated'] += 1
                    else:
                        counts['unchanged'] += 1
                model.objects.bulk_create(created, batch_size=500)
                fields = [f.name for f in model._meta.fields if f.name not in ('id', 'source_id')]
                model.objects.bulk_update(updated, fields, batch_size=500)
                maps[model] = dict(model.objects.values_list('source_id', 'id'))
                report[sheet] = counts

            # Preserve remaining entities for subsequent migrations without pretending their business logic is migrated.
            for sheet in set(KEYS) - {'Banks', 'Client Offices', 'Contacts', 'Leads', 'Cases'}:
                existing = {r.source_id: r for r in SourceRecord.objects.filter(sheet=sheet)}
                creates, updates = [], []
                unchanged = 0
                for row in sheets[sheet]:
                    key = row[KEYS[sheet]]
                    obj = existing.get(key)
                    if obj is None:
                        creates.append(SourceRecord(sheet=sheet, source_id=key, raw=row))
                    elif obj.raw != row:
                        obj.raw = row
                        updates.append(obj)
                    else:
                        unchanged += 1
                SourceRecord.objects.bulk_create(creates, batch_size=500)
                SourceRecord.objects.bulk_update(updates, ['raw'], batch_size=500)
                report[sheet] = {'staged_inserted': len(creates), 'staged_updated': len(updates), 'unchanged': unchanged}
            ImportBatch.objects.create(checksum=checksum, summary=report)
            if options['dry_run']:
                transaction.set_rollback(True)
        self.stdout.write(json.dumps({'dry_run': options['dry_run'], 'sheets': report}, indent=2))
