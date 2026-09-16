import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bank',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ClientType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ContactDesignation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('storage_provider', models.CharField(max_length=40)),
                ('storage_container', models.CharField(blank=True, max_length=300)),
                ('storage_key', models.TextField()),
                ('original_name', models.TextField(blank=True)),
                ('media_type', models.CharField(blank=True, max_length=150)),
                ('size_bytes', models.PositiveBigIntegerField(null=True)),
                ('checksum', models.CharField(blank=True, max_length=64)),
                ('content_verified', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('employee_code', models.CharField(blank=True, db_index=True, max_length=100)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ImportBatch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('snapshot_checksum', models.CharField(max_length=64)),
                ('conversion_version', models.CharField(max_length=80)),
                ('source_environment', models.CharField(max_length=20)),
                ('status', models.CharField(default='staged', max_length=30)),
                ('summary', models.JSONField(default=dict)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(blank=True, max_length=100)),
                ('origin', models.CharField(max_length=40)),
                ('received_date', models.DateField(null=True)),
                ('amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('currency', models.CharField(blank=True, max_length=3)),
                ('verified', models.BooleanField(default=False)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BankBranch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('ifsc', models.CharField(blank=True, db_index=True, max_length=40)),
                ('micr', models.CharField(blank=True, max_length=40)),
                ('address', models.TextField(blank=True)),
                ('city', models.CharField(blank=True, max_length=150)),
                ('district', models.CharField(blank=True, max_length=150)),
                ('state', models.CharField(blank=True, max_length=150)),
                ('bank', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.bank')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ClientOffice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('branch_name', models.CharField(blank=True, max_length=500)),
                ('address', models.TextField(blank=True)),
                ('legacy_working_status', models.CharField(blank=True, max_length=40)),
                ('bank', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.bank')),
                ('directory_branch', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.bankbranch')),
                ('client_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.clienttype')),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.employee')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('phone', models.CharField(blank=True, max_length=80)),
                ('alternate_phone', models.CharField(blank=True, max_length=80)),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.clientoffice')),
                ('designation', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.contactdesignation')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(blank=True, db_index=True, max_length=100)),
                ('origin', models.CharField(max_length=30)),
                ('issued_date', models.DateField(null=True)),
                ('due_date', models.DateField(null=True)),
                ('currency', models.CharField(blank=True, max_length=3)),
                ('billed_amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('legacy_paid_amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('legacy_remaining_amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
                ('office', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.clientoffice')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='InvoiceLine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('net_amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('tax_amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.invoice')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(blank=True, db_index=True, max_length=100)),
                ('received_date', models.DateField(db_index=True, null=True)),
                ('date_basis', models.CharField(default='unknown', max_length=40)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
                ('legacy_deleted', models.CharField(blank=True, max_length=40)),
                ('assigned_employee', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.employee')),
                ('contact', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.contact')),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.clientoffice')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Borrower',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('agreed_fee', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('currency', models.CharField(blank=True, max_length=3)),
                ('property_count', models.PositiveIntegerField(null=True)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.lead')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MigrationIssue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_identity', models.JSONField(default=dict)),
                ('reason', models.TextField()),
                ('resolution', models.TextField(blank=True)),
                ('resolved', models.BooleanField(default=False)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.importbatch')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SalaryBaseline',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
                ('source_variant', models.CharField(max_length=80)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.employee')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SalaryBaselineComponent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pay_code', models.CharField(max_length=80)),
                ('amount', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('from_period', models.CharField(blank=True, max_length=20)),
                ('to_period', models.CharField(blank=True, max_length=20)),
                ('mode', models.CharField(blank=True, max_length=40)),
                ('baseline', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.salarybaseline')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SalaryResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('period', models.CharField(max_length=20)),
                ('gross_earning', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('gross_deduction', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('net_salary', models.DecimalField(decimal_places=6, max_digits=24, null=True)),
                ('paid_days', models.DecimalField(decimal_places=3, max_digits=8, null=True)),
                ('legacy_payment_status', models.CharField(blank=True, max_length=80)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.employee')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ServiceSubtype',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=500)),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.servicetype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RequestedService',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('party_count', models.PositiveIntegerField(null=True)),
                ('case_count', models.PositiveIntegerField(null=True)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.lead')),
                ('subtype', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.servicesubtype')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.servicetype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Case',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset_address', models.TextField(blank=True)),
                ('asset_district', models.CharField(blank=True, max_length=150)),
                ('asset_state', models.CharField(blank=True, max_length=150)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
                ('borrower', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.borrower')),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.lead')),
                ('subtype', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.servicesubtype')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.servicetype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Valuation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('valuation_date', models.DateField(null=True)),
                ('legacy_status', models.CharField(blank=True, max_length=80)),
                ('report_number', models.CharField(blank=True, max_length=100)),
                ('assessor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.employee')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.case')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='invoice',
            name='valuation',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.valuation'),
        ),
        migrations.CreateModel(
            name='WorkOrder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(blank=True, db_index=True, max_length=100)),
                ('legacy_status', models.CharField(blank=True, max_length=40)),
                ('borrower', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.borrower')),
                ('document', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.document')),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.lead')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='valuation',
            name='work_order',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='target_core.workorder'),
        ),
        migrations.CreateModel(
            name='LeaveOpeningBalance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('leave_type_code', models.CharField(max_length=80)),
                ('as_of_date', models.DateField()),
                ('days', models.DecimalField(decimal_places=3, max_digits=10)),
                ('evidence', models.JSONField(default=dict)),
                ('reconciled', models.BooleanField(default=False)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.employee')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('employee', 'leave_type_code', 'as_of_date'), name='leave_opening_balance_unique')],
            },
        ),
        migrations.CreateModel(
            name='ReceiptAllocation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=6, max_digits=24)),
                ('posting_key', models.CharField(max_length=100, unique=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.invoice')),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.receipt')),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='allocation_amount_positive')],
            },
        ),
        migrations.CreateModel(
            name='SourceIdentity',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('environment', models.CharField(max_length=20)),
                ('schema', models.CharField(max_length=80)),
                ('table', models.CharField(max_length=100)),
                ('key', models.CharField(max_length=512)),
                ('target_model', models.CharField(max_length=100)),
                ('target_id', models.UUIDField()),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.importbatch')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('environment', 'schema', 'table', 'key'), name='source_identity_unique')],
            },
        ),
    ]
