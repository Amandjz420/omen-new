"""One-way full refresh from the read-only source database into managed models.

No JSON-export dependency, no hard-coded snapshot dates, no attendance import.
Missing/invalid required references are quarantined with their original payload.
"""
import hashlib
import json
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import connections, transaction
from . import models as m

VERSION = 'mysql-target-v1'
NS = uuid.UUID('9bd83976-1597-4f34-99cf-6ea542f97ebc')

# schema, table, ID, target, scalar target->source, FK target->(parent table, source column, optional)
SPECS = [
 ('uam_user','bank','bank_id',m.Bank,{'name':'name','legacy_status':'status'},{}),
 ('uam_user','bank_branch','branch_id',m.BankBranch,{'name':'name','ifsc':'ifsc_code','micr':'micr_code','address':'branch_address','city':'city','district':'district','state':'state'}, {'bank':('bank','bank_id',False)}),
 ('uam_user','employee','emp_id',m.Employee,{'name':'name','employee_code':'emp_code'},{}),
 ('lead_mngt','client_type','client_type_id',m.ClientType,{'name':'client_type_name'},{}),
 ('lead_mngt','client_designation','client_designation_id',m.ContactDesignation,{'name':'name'},{}),
 ('lead_mngt','service_type','service_type_id',m.ServiceType,{'name':'name'},{}),
 ('lead_mngt','service_sub_type','service_sub_type_id',m.ServiceSubtype,{'name':'name'}, {'service':('service_type','service_type_id',False)}),
 ('lead_mngt','client','client_id',m.ClientOffice,{'name':'name','branch_name':'branch','address':'address','legacy_working_status':'working'}, {'client_type':('client_type','client_type_id',True),'bank':('bank','bank_id',True),'directory_branch':('bank_branch','bank_branch_id',True)}),
 ('lead_mngt','orderer_reg','orderer_reg_id',m.Contact,{'name':'orderer_name','phone':'mobile_no','alternate_phone':'alt_contact_no'}, {'office':('client','client_id',False),'designation':('client_designation','client_designation_id',True)}),
 ('lead_mngt','lead','lead_id',m.Lead,{'number':'lead_no','received_date':'lead_date','legacy_status':'lead_status','legacy_deleted':'delete_status'}, {'office':('client','client_id',False),'contact':('orderer_reg','orderer_reg_id',True),'assigned_employee':('employee','assigned_to',True)}),
 ('lead_mngt','lead_services','lead_service_id',m.RequestedService,{'party_count':'no_of_parties','case_count':'no_of_cases'}, {'lead':('lead','lead_id',False),'service':('service_type','service_type_id',False),'subtype':('service_sub_type','service_sub_type_id',True)}),
 ('lead_mngt','lead_borrower','lead_borrower_id',m.Borrower,{'name':'name_of_borrower','agreed_fee':'wo_amount','property_count':'no_of_properties'}, {'lead':('lead','lead_id',False)}),
 ('lead_mngt','client_customer','client_customer_id',m.Case,{'asset_address':'address','legacy_status':'delete_status'}, {'lead':('lead','lead_id',False),'borrower':('lead_borrower','lead_borrower_id',False),'service':('service_type','service_type_id',False),'subtype':('service_sub_type','service_sub_type_id',True)}),
 ('lead_mngt','upload','upload_id',m.Document,{'storage_key':'doc_path','original_name':'doc_name','media_type':'doc_type_name','size_bytes':'doc_size'},{}),
 ('lead_mngt','lead_order','lead_order_id',m.WorkOrder,{'number':'lead_order_no','legacy_status':'status'}, {'lead':('lead','lead_id',False),'borrower':('lead_borrower','lead_borrower_id',False),'document':('upload','upload_id',True)}),
 ('lead_mngt','valuation','valuation_id',m.Valuation,{'valuation_date':'valuation_date','legacy_status':'valuation_status','report_number':'report_no'}, {'case':('client_customer','client_customer_id',False),'work_order':('lead_order','lead_order_id',True),'assessor':('employee','valuation_done_by',True)}),
 ('lead_mngt','invoice','invoice_id',m.Invoice,{'number':'invoice_no','issued_date':'invoice_date','due_date':'due_date','billed_amount':'total_invoice_amount','legacy_paid_amount':'total_pay_amount','legacy_remaining_amount':'total_remaining_amount','legacy_status':'payment_status'}, {'valuation':('valuation','valuation_id',False)}),
 ('lead_mngt','cash_receipt','cash_receipt_id',m.Receipt,{'number':'cash_receipt_no','received_date':'date','amount':'ammount','legacy_status':'payment_status'},{}),
 ('lead_mngt','amount_received','amount_received_id',m.Receipt,{'received_date':'payment_date','amount':'amount_received','legacy_status':'verify_status'},{}),
 ('uam_user','employee_salary_main_backup','employee_salary_main_id',m.SalaryBaseline,{'legacy_status':'status'}, {'employee':('employee','emp_id',False)}),
 ('uam_user','employee_salary_backup','employee_salary_id',m.SalaryBaselineComponent,{'pay_code':'pay_code','amount':'amount','from_period':'from_year_month','to_period':'to_year_month','mode':'pay_mode'}, {'baseline':('employee_salary_main_backup','employee_salary_main_id',False)}),
 ('uam_user','employee_salary_summary','employee_salary_summary_id',m.SalaryResult,{'period':'year_months','gross_earning':'gross_earning','gross_deduction':'gross_deduction','net_salary':'net_salary','paid_days':'present_days','legacy_payment_status':'transaction_status'}, {'employee':('employee','employee_id',False)}),
]
ALLOWED = {(s,t) for s,t,*_ in SPECS} | {('uam_user','state'),('uam_user','district')}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), default=str)


def source_key(value):
    if value is None or str(value)=='':
        raise ValueError('Missing source ID')
    return canonical([['id',str(value)]])


class MySQLSource:
    """One read-only connection reads both main schemas. Never writes to the source."""
    @contextmanager
    def snapshot(self):
        if 'lead_mngt' not in connections:
            raise ValueError('Use --settings=config.full_database to configure the MySQL source')
        self.connection = connections['lead_mngt']
        if self.connection.vendor != 'mysql':
            raise ValueError('The legacy connection must use MySQL/MariaDB')
        with self.connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
        try:
            yield self
        finally:
            self.connection.rollback()

    def rows(self, schema, table):
        if (schema,table) not in ALLOWED:
            raise ValueError('Table outside import contract')
        with self.connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM `{schema}`.`{table}`')
            columns=[c[0].lower() for c in cursor.description]
            return [dict(zip(columns,row)) for row in cursor.fetchall()]


def convert(field, value, warnings, source_column):
    if isinstance(field, (m.models.CharField,m.models.TextField)):
        return '' if value is None else str(value)
    if value in (None,''):
        return None
    if isinstance(field,m.models.DateField):
        try:
            parsed=date.fromisoformat(str(value)[:10])
            if parsed.year < 1900: raise ValueError()
            return parsed
        except ValueError:
            warnings.append(f'Invalid date in {source_column}; raw value retained')
            return None
    if isinstance(field,m.models.DecimalField):
        result=Decimal(str(value))
        if not result.is_finite(): raise ValueError(f'Invalid decimal in {source_column}')
        return result
    if isinstance(field,m.models.IntegerField):
        number=Decimal(str(value))
        if not number.is_finite() or number!=number.to_integral_value() or number<0:
            raise ValueError(f'Invalid count in {source_column}')
        return int(number)
    return value


def synchronize(source, *, dry_run=False, progress=lambda message: None):
    """All target rows commit atomically; one failed batch record survives failure.

    Rows invalid under target constraints remain in SourceRow quarantine. An existing
    good target is not overwritten with a now-invalid source correction.
    """
    batch=m.ImportBatch.objects.create(snapshot_checksum='',conversion_version=VERSION,source_environment='main',status='running')
    report={}
    digest=hashlib.sha256()
    try:
        with source.snapshot(), transaction.atomic():
            maps={}
            geo={name:{str(r[name+'_id']):r['name'] or '' for r in source.rows('uam_user',name)} for name in ('state','district')}
            for schema,table,keycol,model,scalars,links in SPECS:
                progress(f'Reading {schema}.{table}')
                rows=source.rows(schema,table)
                identities={r.key:r for r in m.SourceIdentity.objects.filter(environment='main',schema=schema,table=table)}
                existing={r.id:r for r in model.objects.filter(id__in=[r.target_id for r in identities.values()])}
                stages={r.key:r for r in m.SourceRow.objects.filter(schema=schema,table=table)}
                counts={'source_rows':len(rows),'inserted':0,'updated':0,'unchanged':0,'quarantined':0,'rows_with_issues':0}
                creates,updates,identity_creates,stage_creates,stage_updates,issues=[],[],[],[],[],[]
                current={}
                seen=set()
                # Sort by canonical source ID for a deterministic fingerprint independent of SQL row order.
                rows.sort(key=lambda r:source_key(r[keycol]))
                for row in rows:
                    required={keycol,*scalars.values(),*(link[1] for link in links.values())}
                    if required-set(row):
                        raise ValueError(f'Source contract missing columns in {schema}.{table}: {sorted(required-set(row))}')
                    key=source_key(row[keycol])
                    if key in seen: raise ValueError(f'Duplicate source key in {schema}.{table}; no arbitrary match selected')
                    seen.add(key)
                    payload=json.loads(canonical(row)); fingerprint=hashlib.sha256(canonical(payload).encode()).hexdigest()
                    digest.update(canonical([schema,table,key,fingerprint]).encode())
                    warnings=[]; values={}; problem=None
                    ident=identities.get(key)
                    obj=existing.get(ident.target_id) if ident else None
                    if ident and obj is None: raise ValueError('Source identity refers to a missing target; repair before import')
                    try:
                        for field,column in scalars.items():
                            f=model._meta.get_field(field)
                            value=convert(f,row[column],warnings,column)
                            f.run_validators(value)
                            values[field]=value
                        for field,(parent,column,optional) in links.items():
                            source_id=row[column]
                            linked=maps[parent].get(str(source_id))
                            values[field+'_id']=linked.id if linked else None
                            if linked is None and not optional:
                                raise ValueError(f'Missing or quarantined required parent: {column}')
                            if linked is None and source_id not in (None,'',0,'0'):
                                warnings.append(f'Unmatched optional parent: {column}')
                        if model is m.ClientOffice:
                            values.update(state=geo['state'].get(str(row['state_id']),''),district=geo['district'].get(str(row['district_id']),''))
                            directory=maps['bank_branch'].get(str(row['bank_branch_id']))
                            if directory and values['bank_id'] and directory.bank_id!=values['bank_id']:
                                raise ValueError('Office bank disagrees with directory branch bank')
                        if model is m.Lead: values['date_basis']='lead_entry_proxy'
                        if model is m.Document: values['storage_provider']='legacy_lead_storage'
                        if model is m.Invoice: values['origin']='legacy_invoice'
                        if model is m.Receipt: values['origin']='legacy_'+table
                        if model is m.SalaryBaseline: values['source_variant']=table
                        if model in (m.RequestedService,m.Case):
                            subtype=maps['service_sub_type'].get(str(row['service_sub_type_id']))
                            if subtype and subtype.service_id!=values['service_id']:
                                raise ValueError('Subtype belongs to a different service')
                        if model in (m.Case,m.WorkOrder):
                            borrower=maps['lead_borrower'][str(row['lead_borrower_id'])]
                            if borrower.lead_id!=values['lead_id']: raise ValueError('Borrower belongs to a different lead')
                        if model is m.Valuation and values['work_order_id']:
                            order=maps['lead_order'][str(row['lead_order_id'])]; case=maps['client_customer'][str(row['client_customer_id'])]
                            if order.lead_id!=case.lead_id or order.borrower_id!=case.borrower_id:
                                raise ValueError('Valuation case and order refer to different lead/borrower')
                        if obj is None:
                            obj=model(id=uuid.uuid5(NS,f'{schema}.{table}:{key}'),**values)
                            creates.append(obj); counts['inserted']+=1
                            identity_creates.append(m.SourceIdentity(batch=batch,environment='main',schema=schema,table=table,key=key,target_model=model._meta.label,target_id=obj.id))
                        elif any(getattr(obj,k)!=v for k,v in values.items()):
                            for k,v in values.items(): setattr(obj,k,v)
                            obj.updated_at=datetime.now().astimezone(); updates.append(obj); counts['updated']+=1
                        else: counts['unchanged']+=1
                        current[str(row[keycol])]=obj
                    except (ValueError,InvalidOperation,ValidationError) as exc:
                        problem=str(exc) if not isinstance(exc,ValidationError) else 'Value violates target field limits'
                        warnings.append(problem); counts['quarantined']+=1
                    if warnings:
                        counts['rows_with_issues']+=1
                        issues.append(m.MigrationIssue(batch=batch,source_identity={'schema':schema,'table':table,'key':key},reason='; '.join(warnings)))
                    outcome='quarantined' if problem else 'imported'
                    prior=stages.get(key)
                    values_stage=dict(payload=payload,payload_hash=fingerprint,batch=batch,outcome=outcome,problems=warnings)
                    if prior is None: stage_creates.append(m.SourceRow(schema=schema,table=table,key=key,**values_stage))
                    elif prior.payload_hash!=fingerprint or prior.outcome!=outcome or prior.problems!=warnings:
                        for k,v in values_stage.items():setattr(prior,k,v)
                        stage_updates.append(prior)
                model.objects.bulk_create(creates,batch_size=400)
                # Only import-owned fields are updated: local office owner and note rows are untouched.
                update_fields=[*scalars,*links]
                extra={m.ClientOffice:['state','district'],m.Lead:['date_basis'],m.Document:['storage_provider'],m.Invoice:['origin'],m.Receipt:['origin'],m.SalaryBaseline:['source_variant']}.get(model,[])
                model.objects.bulk_update(updates,update_fields+extra+['updated_at'],batch_size=300)
                m.SourceIdentity.objects.bulk_create(identity_creates,batch_size=400)
                m.SourceRow.objects.bulk_create(stage_creates,batch_size=300)
                m.SourceRow.objects.bulk_update(stage_updates,['payload','payload_hash','batch','outcome','problems'],batch_size=250)
                m.MigrationIssue.objects.bulk_create(issues,batch_size=400)
                maps[table]=current
                assert sum(counts[k] for k in ('inserted','updated','unchanged','quarantined'))==counts['source_rows']
                report[table]=counts
                progress(f'{table}: {counts}')
            batch.snapshot_checksum=digest.hexdigest(); batch.summary=report
            batch.status='completed_with_issues' if any(r['rows_with_issues'] for r in report.values()) else 'completed'
            batch.save()
            if dry_run: transaction.set_rollback(True)
        if dry_run: batch.delete()
        return report
    except Exception:
        if dry_run: batch.delete()
        else:
            batch.status='failed'; batch.summary={'error':'Import rolled back; inspect command error and correct input before retrying'}; batch.save()
        raise
