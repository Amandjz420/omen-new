from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.contrib.auth.models import User
from django.test import TestCase
from .models import Bank, BankBranch, ClientOffice, Employee, ImportBatch, SourceIdentity, SalaryResult, Receipt, Invoice, ReceiptAllocation


class TargetSchemaTests(TestCase):
    def test_directory_branch_and_client_office_have_separate_identity(self):
        bank=Bank.objects.create(name='Bank')
        branch=BankBranch.objects.create(bank=bank,name='Main',ifsc='001ABC')
        office=ClientOffice.objects.create(name='Office',bank=bank,directory_branch=branch)
        self.assertNotEqual(branch.id,office.id)
        self.assertEqual(branch.ifsc,'001ABC')
        with self.assertRaises(ProtectedError): bank.delete()

    def test_source_identity_is_namespaced_and_repeat_key_rejected(self):
        batch=ImportBatch.objects.create(snapshot_checksum='a'*64,conversion_version='1',source_environment='main')
        target=Bank.objects.create(name='Bank')
        fields=dict(batch=batch,environment='main',schema='uam_user',table='bank',key='[["int",1]]',target_model='target_core.Bank',target_id=target.id)
        SourceIdentity.objects.create(**fields)
        with self.assertRaises(IntegrityError),transaction.atomic(): SourceIdentity.objects.create(**fields)
        fields['environment']='uat'
        SourceIdentity.objects.create(**fields)
        self.assertEqual(SourceIdentity.objects.count(),2)

    def test_historical_salary_survives_without_attendance(self):
        employee=Employee.objects.create(name='Employee')
        result=SalaryResult.objects.create(employee=employee,period='2026-08',net_salary=Decimal('12345.678901'),paid_days=Decimal('29.5'))
        result.refresh_from_db()
        self.assertEqual(result.net_salary,Decimal('12345.678901'))
        self.assertEqual(result.paid_days,Decimal('29.500'))

    def test_allocation_requires_positive_amount_and_idempotency_key(self):
        receipt=Receipt.objects.create(origin='new',amount=100)
        invoice=Invoice.objects.create(origin='new',billed_amount=100)
        fields=dict(receipt=receipt,invoice=invoice,amount=10,posting_key='receipt-entry-1')
        ReceiptAllocation.objects.create(**fields)
        with self.assertRaises(IntegrityError),transaction.atomic(): ReceiptAllocation.objects.create(**fields)
        fields.update(amount=0,posting_key='receipt-entry-2')
        with self.assertRaises(IntegrityError),transaction.atomic(): ReceiptAllocation.objects.create(**fields)


# ---------------------------------------------------------------------------
# Importer pipeline tests.
#
# These drive synchronize() through a fake source so the paging, correction and
# quarantine paths are exercised without MySQL. Fixture rows are generated from
# SPECS itself, so a spec change surfaces here rather than at import time.
# ---------------------------------------------------------------------------

from contextlib import contextmanager
from .models import (Case, ClientOffice, Document, Employee, Lead, LeadNote, Question,
                     QuestionOption, ServiceSubtype, SourceRow, ValuationAnswer)
from .sync import SPECS, synchronize

SPEC_BY = {(s, t): (k, model, scalars, links) for s, t, k, model, scalars, links in SPECS}


def row(schema, table, **overrides):
    """Build a source row carrying exactly the columns the spec declares."""
    key, model, scalars, links = SPEC_BY[(schema, table)]
    columns = {key, *scalars.values(), *(link[1] for link in links.values())}
    if model.__name__ == 'ClientOffice':
        columns |= {'state_id', 'district_id'}
    record = {column: None for column in columns}
    record.update(overrides)
    return record


class FakeSource:
    def __init__(self, data, page_size=1000):
        self.data = data
        self.page_size = page_size

    @contextmanager
    def snapshot(self):
        yield

    def rows(self, schema, table):
        return list(self.data.get((schema, table), []))

    def chunks(self, schema, table, keycol, size=None):
        ordered = sorted(self.data.get((schema, table), []), key=lambda r: str(r[keycol]))
        for start in range(0, len(ordered), self.page_size):
            yield ordered[start:start + self.page_size]


def dataset(extra=None):
    """A minimal bank -> office -> lead -> borrower -> case chain."""
    data = {
        ('uam_user', 'bank'): [row('uam_user', 'bank', bank_id=1, name='Bank', status='1')],
        ('lead_mngt', 'client_type'): [row('lead_mngt', 'client_type', client_type_id=1, client_type_name='Public')],
        ('lead_mngt', 'service_type'): [row('lead_mngt', 'service_type', service_type_id=1, name='Valuation')],
        ('lead_mngt', 'service_sub_type'): [row('lead_mngt', 'service_sub_type', service_sub_type_id=1, name='L & B', service_type_id=1)],
        ('lead_mngt', 'client'): [row('lead_mngt', 'client', client_id=1, name='Office', branch='Main', bank_id=1, client_type_id=1)],
        ('lead_mngt', 'lead'): [row('lead_mngt', 'lead', lead_id=1, lead_no='L-1', client_id=1)],
        ('lead_mngt', 'lead_borrower'): [row('lead_mngt', 'lead_borrower', lead_borrower_id=1, name_of_borrower='Borrower', lead_id=1)],
        ('lead_mngt', 'client_customer'): [row('lead_mngt', 'client_customer', client_customer_id=1, lead_id=1, lead_borrower_id=1, service_type_id=1, service_sub_type_id=1)],
    }
    data.update(extra or {})
    return data


class ImporterPipelineTests(TestCase):
    def run_import(self, data, page_size=1000, **kwargs):
        return synchronize(FakeSource(data, page_size=page_size), **kwargs)

    def test_repeat_import_across_page_boundaries_changes_nothing(self):
        data = dataset()
        first = self.run_import(data, page_size=1)
        self.assertEqual(sum(t['inserted'] for t in first.values()), 8)
        second = self.run_import(data, page_size=1)
        self.assertEqual(sum(t['inserted'] for t in second.values()), 0)
        self.assertEqual(sum(t['updated'] for t in second.values()), 0)
        self.assertEqual(sum(t['unchanged'] for t in second.values()), 8)
        self.assertEqual(Case.objects.count(), 1)

    def test_paging_does_not_drop_rows(self):
        extra = [row('lead_mngt', 'lead_borrower', lead_borrower_id=n, name_of_borrower=f'B{n}', lead_id=1)
                 for n in range(1, 8)]
        data = dataset({('lead_mngt', 'lead_borrower'): extra})
        self.run_import(data, page_size=2)
        self.assertEqual(SourceRow.objects.filter(table='lead_borrower').count(), 7)

    def test_missing_required_parent_quarantines_and_keeps_payload(self):
        data = dataset({('lead_mngt', 'lead_borrower'): [
            row('lead_mngt', 'lead_borrower', lead_borrower_id=1, name_of_borrower='Orphan', lead_id=999)]})
        report = self.run_import(data)
        self.assertEqual(report['lead_mngt.lead_borrower']['quarantined'], 1)
        staged = SourceRow.objects.get(table='lead_borrower')
        self.assertEqual(staged.outcome, 'quarantined')
        self.assertEqual(staged.payload['name_of_borrower'], 'Orphan')
        self.assertTrue(any('lead_id' in problem for problem in staged.problems))

    def test_zero_padded_borrower_reference_resolves_and_import_completes(self):
        """Regression: the resolver normalizes padded keys, but the later borrower
        check used the raw string and raised an uncaught KeyError, aborting the run."""
        data = dataset({('lead_mngt', 'client_customer'): [
            row('lead_mngt', 'client_customer', client_customer_id=1, lead_id='0001',
                lead_borrower_id='0001', service_type_id=1, service_sub_type_id=1)]})
        report = self.run_import(data)
        self.assertEqual(report['lead_mngt.client_customer']['quarantined'], 0)
        self.assertEqual(Case.objects.count(), 1)

    def test_padded_branch_reference_is_still_validated(self):
        """A padded reference must be checked, not silently skipped."""
        data = dataset({
            ('uam_user', 'bank'): [row('uam_user', 'bank', bank_id=1, name='Bank'),
                                   row('uam_user', 'bank', bank_id=2, name='Other')],
            ('uam_user', 'bank_branch'): [row('uam_user', 'bank_branch', branch_id=7, name='Branch', bank_id=2)],
            ('lead_mngt', 'client'): [row('lead_mngt', 'client', client_id=1, name='Office',
                                          bank_id=1, client_type_id=1, bank_branch_id='0007')]})
        report = self.run_import(data)
        self.assertEqual(report['lead_mngt.client']['quarantined'], 1)
        self.assertIn('directory branch bank', ' '.join(SourceRow.objects.get(table='client').problems))

    def test_subtype_filed_under_another_service_is_remapped_by_name(self):
        data = dataset({
            ('lead_mngt', 'service_type'): [row('lead_mngt', 'service_type', service_type_id=1, name='Valuation'),
                                            row('lead_mngt', 'service_type', service_type_id=2, name='Other')],
            ('lead_mngt', 'service_sub_type'): [
                row('lead_mngt', 'service_sub_type', service_sub_type_id=1, name='L & B ', service_type_id=1),
                row('lead_mngt', 'service_sub_type', service_sub_type_id=2, name='l & b', service_type_id=2)],
            ('lead_mngt', 'client_customer'): [
                row('lead_mngt', 'client_customer', client_customer_id=1, lead_id=1, lead_borrower_id=1,
                    service_type_id=1, service_sub_type_id=2)]})
        self.run_import(data)
        case = Case.objects.get()
        self.assertEqual(case.subtype, ServiceSubtype.objects.get(name='L & B '))
        self.assertIn('remapped', ' '.join(SourceRow.objects.get(table='client_customer').problems))

    def test_ambiguous_subtype_name_is_cleared_rather_than_guessed(self):
        data = dataset({
            ('lead_mngt', 'service_type'): [row('lead_mngt', 'service_type', service_type_id=1, name='Valuation'),
                                            row('lead_mngt', 'service_type', service_type_id=2, name='Other')],
            ('lead_mngt', 'service_sub_type'): [
                row('lead_mngt', 'service_sub_type', service_sub_type_id=1, name='L & B', service_type_id=1),
                row('lead_mngt', 'service_sub_type', service_sub_type_id=3, name='l & b ', service_type_id=1),
                row('lead_mngt', 'service_sub_type', service_sub_type_id=2, name='L & B', service_type_id=2)],
            ('lead_mngt', 'client_customer'): [
                row('lead_mngt', 'client_customer', client_customer_id=1, lead_id=1, lead_borrower_id=1,
                    service_type_id=1, service_sub_type_id=2)]})
        self.run_import(data)
        self.assertIsNone(Case.objects.get().subtype)
        self.assertIn('ambiguous', ' '.join(SourceRow.objects.get(table='client_customer').problems))

    def test_answer_option_from_another_question_is_cleared(self):
        data = dataset({
            ('lead_mngt', 'lead_order'): [row('lead_mngt', 'lead_order', lead_order_id=1, lead_id=1, lead_borrower_id=1)],
            ('lead_mngt', 'valuation'): [row('lead_mngt', 'valuation', valuation_id=1, client_customer_id=1, lead_order_id=1)],
            ('lead_mngt', 'question'): [row('lead_mngt', 'question', question_id=1, question='Q1'),
                                        row('lead_mngt', 'question', question_id=2, question='Q2')],
            ('lead_mngt', 'question_options'): [row('lead_mngt', 'question_options', option_id=5, question_id=2, value='Other')],
            ('lead_mngt', 'valuation_answer'): [
                row('lead_mngt', 'valuation_answer', answer_id=1, valuation_id=1, question_id=1,
                    option_id=5, answer_group=0, value='kept')]})
        self.run_import(data)
        answer = ValuationAnswer.objects.get()
        self.assertEqual(answer.value, 'kept')
        self.assertIsNone(answer.option)
        self.assertEqual(answer.question, Question.objects.get(text='Q1'))
        staged = SourceRow.objects.get(table='valuation_answer')
        self.assertEqual(staged.payload['option_id'], 5)
        self.assertIn('different question', ' '.join(staged.problems))

    def test_document_storage_provider_follows_source_system(self):
        data = dataset({
            ('lead_mngt', 'upload'): [row('lead_mngt', 'upload', upload_id=1, doc_path='s3/a.pdf')],
            ('uam_user', 'upload'): [row('uam_user', 'upload', upload_id=1, doc_path='/opt/b.pdf')]})
        self.run_import(data)
        self.assertEqual(Document.objects.get(storage_key='s3/a.pdf').storage_provider, 'legacy_lead_s3')
        self.assertEqual(Document.objects.get(storage_key='/opt/b.pdf').storage_provider, 'legacy_uam_local')

    def test_workspace_notes_survive_a_repeat_import(self):
        data = dataset()
        self.run_import(data)
        user = User.objects.create_user('staff', password='x')
        LeadNote.objects.create(lead=Lead.objects.get(), author=user, body='Called the office')
        self.run_import(data)
        self.assertEqual(LeadNote.objects.get().body, 'Called the office')

    def test_dry_run_leaves_no_target_rows(self):
        self.run_import(dataset(), dry_run=True)
        self.assertEqual(Case.objects.count(), 0)
        self.assertEqual(SourceRow.objects.count(), 0)


# ---------------------------------------------------------------------------
# Account provisioning. Separate from the importer: the importer records what
# the legacy system held, provisioning decides who may sign in.
# ---------------------------------------------------------------------------

from django.core.management import call_command
from .models import LegacyAccount, LegacyProject, RoleAssignment, RoleDefinition


class ProvisioningTests(TestCase):
    def setUp(self):
        self.lead = LegacyProject.objects.create(name='LEAD')
        self.other = LegacyProject.objects.create(name='PAYROLL')
        self.role = RoleDefinition.objects.create(name='Field Assessors', project=self.lead)

    def account(self, login, name, employee=True, project=None, status='1'):
        emp = Employee.objects.create(name=name) if employee else None
        acc = LegacyAccount.objects.create(name=name, login_id=login, employee=emp, legacy_status=status)
        if project is not None:
            RoleAssignment.objects.create(account=acc, role=self.role, project=project,
                                          legacy_status='1', legacy_deleted='0')
        return acc

    def test_provisions_only_accounts_with_lead_access(self):
        self.account('9000000001', 'Assessor', project=self.lead)
        self.account('9000000002', 'Payroll Clerk', project=self.other)
        self.account('9000000003', 'No Access')
        call_command('provision_accounts', verbosity=0)
        self.assertEqual(list(User.objects.values_list('username', flat=True)), ['9000000001'])

    def test_provisioning_is_idempotent(self):
        self.account('9000000001', 'Assessor', project=self.lead)
        call_command('provision_accounts', verbosity=0)
        call_command('provision_accounts', verbosity=0)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Employee.objects.filter(user__isnull=False).count(), 1)

    def test_initial_password_is_the_login_id_and_must_be_changed(self):
        account = self.account('9000000001', 'Assessor', project=self.lead)
        call_command('provision_accounts', verbosity=0)
        account.refresh_from_db()
        self.assertTrue(account.user.check_password('9000000001'))
        self.assertTrue(account.must_change_password)
        self.assertIsNotNone(account.provisioned_at)

    def test_no_account_is_ever_given_superuser(self):
        self.account('9000000001', 'Administrator', project=self.lead)
        call_command('provision_accounts', verbosity=0)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 0)

    def test_employee_without_a_login_keeps_its_assignments(self):
        orphan = Employee.objects.create(name='Retired Assessor')
        office = ClientOffice.objects.create(name='Office')
        lead = Lead.objects.create(office=office, date_basis='lead_entry_proxy', assigned_employee=orphan)
        call_command('provision_accounts', verbosity=0)
        orphan.refresh_from_db()
        self.assertIsNone(orphan.user_id)
        self.assertEqual(lead.assigned_employee, orphan)

    def test_password_validators_remain_enforced_for_chosen_passwords(self):
        """set_password bypasses validators by design; validate_password must not."""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            validate_password('9000000001')
