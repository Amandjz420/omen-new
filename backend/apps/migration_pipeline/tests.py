from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.contrib.auth.models import User
from django.test import TestCase
from target_core.models import Bank, BankBranch, ClientOffice, Employee, ImportBatch, SourceIdentity, SalaryResult, Receipt, Invoice, ReceiptAllocation


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
from target_core.models import (Case, ClientOffice, Document, Employee, Lead, LeadNote, Question,
                     QuestionOption, ServiceSubtype, SourceRow, ValuationAnswer)
from target_core.sync import SPECS, source_key, synchronize

SPEC_BY = {(s, t): (k, model, scalars, links) for s, t, k, model, scalars, links in SPECS}


def row(schema, table, **overrides):
    """Build a source row carrying exactly the columns the spec declares."""
    key, model, scalars, links = SPEC_BY[(schema, table)]
    columns = {key, *scalars.values(), *(link[1] for link in links.values())}
    if model.__name__ in ('ClientOffice', 'Case'):
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
from target_core.models import LegacyAccount, LegacyProject, RoleAssignment, RoleDefinition


class ProvisioningHarness:
    """Shared fixtures. Not a TestCase, so subclasses do not re-run its tests."""

    def setUp(self):
        self.lead = LegacyProject.objects.create(name='LEAD')
        self.other = LegacyProject.objects.create(name='PAYROLL')
        self.role = RoleDefinition.objects.create(name='Field Assessors', project=self.lead,
                                                  legacy_status='1', legacy_deleted='0')

    def account(self, login, name, employee=True, project=None, status='1'):
        emp = Employee.objects.create(name=name) if employee else None
        acc = LegacyAccount.objects.create(name=name, login_id=login, employee=emp, legacy_status=status)
        if project is not None:
            RoleAssignment.objects.create(account=acc, role=self.role, project=project,
                                          legacy_status='1', legacy_deleted='0')
        return acc


class ProvisioningTests(ProvisioningHarness, TestCase):
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


# ---------------------------------------------------------------------------
# Behavioural cover for the identity review findings R1-R8.
# ---------------------------------------------------------------------------

from datetime import datetime
from django.core.management import call_command as run
from target_core.models import LoginEvent
from target_core.sync import EXCLUDED_COLUMNS, readable


class CredentialExclusionTests(TestCase):
    def test_reader_drops_credential_columns(self):
        keep, columns = readable(['user_id', 'name', 'password', 'old_password', 'pin_no', 'session_id'])
        self.assertEqual(columns, ['user_id', 'name'])
        self.assertEqual(keep, [0, 1])

    def test_credential_columns_never_reach_a_staged_payload(self):
        """Even if a credential column reaches the pipeline, it must not persist."""
        rows = dataset()[('uam_user', 'bank')]
        rows[0].update({'password': 'must-not-persist', 'old_password': 'nor-this',
                        'session_id': 'nor-this-either', 'pin_no': '0000'})
        synchronize(FakeSource(dataset({('uam_user', 'bank'): rows})))
        for staged in SourceRow.objects.all():
            self.assertFalse(set(staged.payload) & EXCLUDED_COLUMNS,
                             f'{staged.table} payload retained {set(staged.payload) & EXCLUDED_COLUMNS}')

    def test_no_currently_staged_payload_holds_credentials(self):
        for staged in SourceRow.objects.all():
            self.assertFalse(set(staged.payload) & EXCLUDED_COLUMNS)


class LoginTimestampTests(TestCase):
    def test_login_timestamps_keep_time_of_day(self):
        data = dataset({('uam_user', 'userdetail'): [row('uam_user', 'userdetail', user_id=1, name='A', login_id='9000000001')],
                        ('uam_user', 'login_history'): [row('uam_user', 'login_history', history_id=1, user_id=1,
                                                            login_date='2021-11-27 10:25:16',
                                                            logout_date='2021-11-27 18:40:02')]})
        synchronize(FakeSource(data))
        from django.utils import timezone as tz
        event = LoginEvent.objects.get()
        local_in, local_out = tz.localtime(event.login_at), tz.localtime(event.logout_at)
        self.assertEqual((local_in.hour, local_in.minute, local_in.second), (10, 25, 16))
        self.assertEqual((local_out.hour, local_out.minute), (18, 40))
        self.assertGreater(event.logout_at, event.login_at)


class OnboardingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('9000000001', password='9000000001', is_staff=True)
        self.employee = Employee.objects.create(name='Assessor', user=self.user)
        self.account = LegacyAccount.objects.create(name='Assessor', login_id='9000000001',
                                                    employee=self.employee, user=self.user,
                                                    legacy_status='1', must_change_password=True)

    def test_business_access_blocked_until_password_is_changed(self):
        self.client.force_login(self.user)
        blocked = self.client.get('/api/leads/')
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()['code'], 'password_change_required')

    def test_existing_session_cannot_bypass_onboarding(self):
        self.client.force_login(self.user)
        self.client.get('/api/leads/')
        self.assertEqual(self.client.get('/api/summary/').status_code, 403)

    def test_changing_the_password_clears_the_restriction(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/password/',
                                    {'current_password': '9000000001', 'new_password': 'Kestrel-Harbour-72'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertFalse(self.account.must_change_password)
        self.assertEqual(self.client.get('/api/leads/').status_code, 200)

    def test_a_weak_chosen_password_is_rejected_and_nothing_changes(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/password/',
                                    {'current_password': '9000000001', 'new_password': '9000000001'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()['problems'])
        self.account.refresh_from_db()
        self.assertTrue(self.account.must_change_password)

    def test_wrong_current_password_is_refused(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/api/password/',
                                          {'current_password': 'wrong', 'new_password': 'Kestrel-Harbour-72'},
                                          content_type='application/json').status_code, 400)


class GrantEligibilityTests(ProvisioningHarness, TestCase):
    """R6: a grant must carry a real, enabled role belonging to its own project."""

    def test_grant_without_a_role_provisions_nothing(self):
        acc = self.account('9000000001', 'Assessor')
        RoleAssignment.objects.create(account=acc, role=None, project=self.lead,
                                      legacy_status='1', legacy_deleted='0')
        run('provision_accounts', verbosity=0)
        self.assertEqual(User.objects.count(), 0)

    def test_grant_with_a_deleted_role_provisions_nothing(self):
        dead = RoleDefinition.objects.create(name='Retired', project=self.lead,
                                             legacy_status='1', legacy_deleted='1')
        acc = self.account('9000000001', 'Assessor')
        RoleAssignment.objects.create(account=acc, role=dead, project=self.lead,
                                      legacy_status='1', legacy_deleted='0')
        run('provision_accounts', verbosity=0)
        self.assertEqual(User.objects.count(), 0)

    def test_role_from_another_project_provisions_nothing(self):
        foreign = RoleDefinition.objects.create(name='Payroll Clerk', project=self.other,
                                               legacy_status='1', legacy_deleted='0')
        acc = self.account('9000000001', 'Assessor')
        RoleAssignment.objects.create(account=acc, role=foreign, project=self.lead,
                                      legacy_status='1', legacy_deleted='0')
        run('provision_accounts', verbosity=0)
        self.assertEqual(User.objects.count(), 0)


class RevocationTests(ProvisioningHarness, TestCase):
    """R4: withdrawing the legacy grant or account must withdraw Django access."""

    def test_revoking_the_grant_deactivates_the_django_account(self):
        acc = self.account('9000000001', 'Assessor', project=self.lead)
        run('provision_accounts', verbosity=0)
        self.assertTrue(User.objects.get().is_active)
        acc.role_assignments.update(legacy_status='0')
        run('provision_accounts', verbosity=0)
        self.assertFalse(User.objects.get().is_active)

    def test_disabling_the_legacy_account_deactivates_the_django_account(self):
        acc = self.account('9000000001', 'Assessor', project=self.lead)
        run('provision_accounts', verbosity=0)
        LegacyAccount.objects.filter(pk=acc.pk).update(legacy_status='0')
        run('provision_accounts', verbosity=0)
        self.assertFalse(User.objects.get().is_active)

    def test_interim_policy_grants_business_access_but_never_superuser(self):
        self.account('9000000001', 'Administrator', project=self.lead)
        run('provision_accounts', verbosity=0)
        user = User.objects.get()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_turning_the_interim_policy_off_withdraws_access(self):
        from target_core.management.commands import provision_accounts as command
        self.account('9000000001', 'Assessor', project=self.lead)
        run('provision_accounts', verbosity=0)
        self.assertTrue(User.objects.get().is_staff)
        command.INTERIM_FULL_ACCESS = False
        try:
            run('provision_accounts', verbosity=0)
            self.assertFalse(User.objects.get().is_staff)
        finally:
            command.INTERIM_FULL_ACCESS = True

    def test_a_personal_account_holding_superuser_loses_it(self):
        self.account('9000000001', 'Assessor', project=self.lead)
        run('provision_accounts', verbosity=0)
        User.objects.filter(username='9000000001').update(is_superuser=True)
        run('provision_accounts', verbosity=0)
        self.assertFalse(User.objects.get().is_superuser)


class IdentityBindingTests(ProvisioningHarness, TestCase):
    """R5: never adopt an unreviewed username, never commit a split identity."""

    def test_existing_username_is_not_adopted_without_review(self):
        intruder = User.objects.create_user('9000000001', password='x', is_superuser=True, is_staff=True)
        self.account('9000000001', 'Assessor', project=self.lead)
        run('provision_accounts', verbosity=0)
        intruder.refresh_from_db()
        self.assertIsNone(LegacyAccount.objects.get().user_id)
        self.assertIsNone(Employee.objects.get().user_id)
        self.assertTrue(intruder.is_superuser)

    def test_employee_already_linked_elsewhere_blocks_a_second_identity(self):
        other = User.objects.create_user('someone-else', password='x')
        acc = self.account('9000000001', 'Assessor', project=self.lead)
        Employee.objects.filter(pk=acc.employee_id).update(user=other)
        run('provision_accounts', verbosity=0)
        self.assertFalse(User.objects.filter(username='9000000001').exists())
        acc.refresh_from_db()
        self.assertIsNone(acc.user_id)


class MergeProvisioningTests(ProvisioningHarness, TestCase):
    """R7: the merge graph resolves before eligibility, in a single run."""

    def test_canonical_is_provisioned_in_one_run_when_only_the_duplicate_has_the_grant(self):
        from target_core.management.commands import provision_accounts as command
        canonical = self.account('1000000000', 'Person')          # sorts first, holds no grant
        self.account('9000000001', 'Person Duplicate', employee=False, project=self.lead)
        original = dict(command.MERGES)
        command.MERGES['9000000001'] = ('1000000000', 'test merge')
        try:
            run('provision_accounts', verbosity=0)
            self.assertTrue(User.objects.filter(username='1000000000').exists())
            self.assertFalse(User.objects.filter(username='9000000001').exists())
            canonical.refresh_from_db()
            self.assertIsNotNone(canonical.user_id)
        finally:
            command.MERGES.clear(); command.MERGES.update(original)

    def test_a_merge_pointing_at_a_missing_account_is_reported_not_applied(self):
        from target_core.management.commands import provision_accounts as command
        self.account('9000000001', 'Person', project=self.lead)
        original = dict(command.MERGES)
        command.MERGES['9000000001'] = ('nonexistent', 'test merge')
        try:
            run('provision_accounts', verbosity=0)
            self.assertEqual(User.objects.count(), 0)
        finally:
            command.MERGES.clear(); command.MERGES.update(original)


class SharedAdminAccountTests(ProvisioningHarness, TestCase):
    """The shared generic logins are administered deliberately, never by the
    username-as-password rule that applies to personal accounts."""

    def setUp(self):
        super().setUp()
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        directory = TemporaryDirectory(prefix='omen-admin-test-')
        self.addCleanup(directory.cleanup)
        self.secret_dir = Path(directory.name)
        override = patch('target_core.management.commands.setup_admin_accounts.SECRET_DIR', self.secret_dir)
        override.start()
        self.addCleanup(override.stop)

    def test_issued_credentials_match_accounts_and_file_is_private(self):
        run('setup_admin_accounts', verbosity=0)
        path = self.secret_dir / 'admin-credentials.txt'
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        for line in path.read_text().splitlines():
            if '\t' in line:
                username, password = line.split('\t', 1)
                self.assertTrue(User.objects.get(username=username).check_password(password))

    def test_setup_issues_a_password_that_is_not_the_username(self):
        LegacyAccount.objects.create(name='Super Administrator', login_id='superadmin', legacy_status='1')
        LegacyAccount.objects.create(name='Administrator', login_id='admin', legacy_status='1')
        run('setup_admin_accounts', verbosity=0)
        for name in ('superadmin', 'admin'):
            user = User.objects.get(username=name)
            self.assertTrue(user.has_usable_password())
            self.assertFalse(user.check_password(name))
            self.assertTrue(user.is_staff)
        self.assertTrue(User.objects.get(username='superadmin').is_superuser)
        self.assertFalse(User.objects.get(username='admin').is_superuser)

    def test_shared_accounts_must_still_change_password_at_first_sign_in(self):
        LegacyAccount.objects.create(name='Super Administrator', login_id='superadmin', legacy_status='1')
        run('setup_admin_accounts', verbosity=0)
        self.assertTrue(LegacyAccount.objects.get(login_id='superadmin').must_change_password)

    def test_setup_does_not_rotate_an_already_safe_password(self):
        LegacyAccount.objects.create(name='Super Administrator', login_id='superadmin', legacy_status='1')
        run('setup_admin_accounts', verbosity=0)
        before = User.objects.get(username='superadmin').password
        run('setup_admin_accounts', verbosity=0)
        self.assertEqual(User.objects.get(username='superadmin').password, before)

    def test_provisioning_never_issues_a_guessable_password_to_a_shared_login(self):
        employee = Employee.objects.create(name='Super Administrator')
        account = LegacyAccount.objects.create(name='Super Administrator', login_id='superadmin',
                                               employee=employee, legacy_status='1')
        RoleAssignment.objects.create(account=account, role=self.role, project=self.lead,
                                      legacy_status='1', legacy_deleted='0')
        run('provision_accounts', verbosity=0)
        self.assertFalse(User.objects.get(username='superadmin').has_usable_password())

    def test_provisioning_does_not_withdraw_shared_login_access(self):
        employee = Employee.objects.create(name='Super Administrator')
        account = LegacyAccount.objects.create(name='Super Administrator', login_id='superadmin',
                                               employee=employee, legacy_status='1')
        RoleAssignment.objects.create(account=account, role=self.role, project=self.lead,
                                      legacy_status='1', legacy_deleted='0')
        run('setup_admin_accounts', verbosity=0)
        run('provision_accounts', verbosity=0)
        user = User.objects.get(username='superadmin')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class AdminSiteTests(TestCase):
    """The admin is a second door onto the same data; the rules must hold there."""

    def setUp(self):
        self.user = User.objects.create_user('9000000001', password='initial-Pass-2026!', is_staff=True,
                                             is_superuser=True)
        self.employee = Employee.objects.create(name='Assessor', user=self.user)
        self.account = LegacyAccount.objects.create(name='Assessor', login_id='9000000001',
                                                    employee=self.employee, user=self.user,
                                                    legacy_status='1', must_change_password=True,
                                                    issued_password_hash=self.user.password)

    def test_admin_requires_a_signed_in_user(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_admin_is_blocked_until_the_password_is_changed(self):
        self.client.force_login(self.user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('password_change', response['Location'])

    def test_password_setup_page_stays_reachable_during_onboarding(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/password_change/').status_code, 200)

    def test_a_password_set_outside_the_password_endpoint_does_not_complete_onboarding(self):
        """Only the account holder's own change completes onboarding (review G8).
        This previously asserted the opposite, by comparing stored hashes; but a
        changed hash proves nothing, since Django rewrites it for an unchanged
        password when it upgrades hashing parameters, and a password set through
        the admin site or a shell is someone else's choice for the user."""
        self.user.set_password('Kestrel-Harbour-72')
        self.user.save()
        self.client.force_login(self.user)
        self.client.get('/admin/')
        self.account.refresh_from_db()
        self.assertTrue(self.account.must_change_password)

    def test_editing_an_imported_record_claims_it_from_the_importer(self):
        """An admin edit must transfer ownership, or the next import overwrites it."""
        from django.contrib import admin as django_admin
        from target_core.models import ImportBatch, LocalRecord, SourceIdentity

        office = ClientOffice.objects.create(name='Imported Office')
        batch = ImportBatch.objects.create(snapshot_checksum='test', conversion_version='test',
                                           source_environment='main')
        SourceIdentity.objects.create(batch=batch, environment='main', schema='lead_mngt', table='client',
                                      key='[["client_id","1"]]', target_model=ClientOffice._meta.label,
                                      target_id=office.pk)

        class Form:
            changed_data = ['name']
            cleaned_data = {'name': 'Renamed Office'}

        class Request:
            user = self.user

        office.name = 'Renamed Office'
        django_admin.site._registry[ClientOffice].save_model(Request(), office, Form(), change=True)

        office.refresh_from_db()
        self.assertEqual(office.name, 'Renamed Office')
        self.assertTrue(LocalRecord.objects.filter(target_model=ClientOffice._meta.label,
                                                   target_id=office.pk).exists())

    def test_editing_a_locally_created_record_does_not_need_a_marker(self):
        """Records the importer never owned need no ownership transfer."""
        from django.contrib import admin as django_admin
        from target_core.models import LocalRecord

        office = ClientOffice.objects.create(name='Local Office')

        class Form:
            changed_data = ['name']
            cleaned_data = {'name': 'Local Office Renamed'}

        class Request:
            user = self.user

        django_admin.site._registry[ClientOffice].save_model(Request(), office, Form(), change=True)
        self.assertFalse(LocalRecord.objects.filter(target_id=office.pk).exists())

    def test_migration_evidence_cannot_be_edited(self):
        from django.contrib import admin as django_admin
        from target_core.models import SourceRow, MigrationIssue, LegacyAccount as LA
        for model in (SourceRow, MigrationIssue, LA):
            registered = django_admin.site._registry[model]
            self.assertFalse(registered.has_change_permission(None))
            self.assertFalse(registered.has_add_permission(None))
            self.assertFalse(registered.has_delete_permission(None))


# ---------------------------------------------------------------------------
# Bank report templates, dispatch and notification history.
# ---------------------------------------------------------------------------

from target_core.models import Dispatch, DispatchItem, ReportTemplate, ReportTemplateLine, SmsMessage, Valuation


class DispatchLinkTests(TestCase):
    def setUp(self):
        office = ClientOffice.objects.create(name='Office')
        self.lead = Lead.objects.create(office=office, date_basis='lead_entry_proxy', number='L-0422223670')
        from target_core.models import Borrower, ServiceType
        service = ServiceType.objects.create(name='Valuation')
        borrower = Borrower.objects.create(lead=self.lead, name='B')
        case = Case.objects.create(lead=self.lead, borrower=borrower, service=service)
        self.v1 = Valuation.objects.create(case=case, report_number='R-0522166405')
        self.v2 = Valuation.objects.create(case=case, report_number='R-0622236817')

    def link(self):
        run('link_dispatch_items', verbosity=0)

    def test_every_reference_is_recorded_with_its_resolution(self):
        d = Dispatch.objects.create(number='D-1', report_references=
            'R-0522166405, R0622236817 ,L-0422223670,R-9999999999')
        self.link()
        items = {i.position: i for i in d.items.all()}
        self.assertEqual(len(items), 4)
        self.assertEqual((items[0].resolution, items[0].valuation), (DispatchItem.EXACT, self.v1))
        self.assertEqual((items[1].resolution, items[1].valuation), (DispatchItem.NORMALIZED, self.v2))
        self.assertEqual((items[2].resolution, items[2].lead), (DispatchItem.LEAD_NUMBER, self.lead))
        self.assertEqual(items[3].resolution, DispatchItem.UNRESOLVED)
        self.assertEqual(items[3].reference, 'R-9999999999')

    def test_a_bare_numeric_reference_gains_its_prefix(self):
        d = Dispatch.objects.create(number='D-2', report_references='0622236817')
        self.link()
        self.assertEqual(d.items.get().valuation, self.v2)

    def test_linking_is_idempotent(self):
        Dispatch.objects.create(number='D-1', report_references='R-0522166405,R-0622236817')
        self.link(); first = sorted(DispatchItem.objects.values_list('id', flat=True))
        self.link(); second = sorted(DispatchItem.objects.values_list('id', flat=True))
        self.assertEqual(first, second)

    def test_a_shrinking_reference_list_removes_surplus_items(self):
        d = Dispatch.objects.create(number='D-1', report_references='R-0522166405,R-0622236817')
        self.link()
        Dispatch.objects.filter(pk=d.pk).update(report_references='R-0522166405')
        self.link()
        self.assertEqual(list(d.items.values_list('valuation', flat=True)), [self.v1.pk])

    def test_a_report_dispatched_twice_links_twice(self):
        Dispatch.objects.create(number='D-1', report_references='R-0522166405')
        Dispatch.objects.create(number='D-2', report_references='R-0522166405')
        self.link()
        self.assertEqual(self.v1.dispatch_items.count(), 2)

    def test_legacy_codes_decode_from_the_legacy_enums(self):
        d = Dispatch.objects.create(number='D-1', mode=2, status=3, courier=2)
        self.assertEqual((d.get_mode_display(), d.get_status_display(), d.get_courier_display()),
                         ('Speed Post', 'Delivered', 'India Post Services'))


class TemplateImportTests(TestCase):
    def test_a_template_with_an_unresolved_subtype_is_kept_not_quarantined(self):
        data = dataset({
            ('lead_mngt', 'report_setup'): [row('lead_mngt', 'report_setup', report_setup_id=1,
                                                client_type_id=1, service_type=1, service_sub_type=999)],
            ('lead_mngt', 'report_question'): [row('lead_mngt', 'report_question', id=1, setup_id=1,
                                                   question_output='Area', sequence=None)]})
        report = synchronize(FakeSource(data))
        self.assertEqual(report['lead_mngt.report_setup']['quarantined'], 0)
        template = ReportTemplate.objects.get()
        self.assertIsNone(template.subtype)
        self.assertEqual(ReportTemplateLine.objects.get().template, template)

    def test_a_line_without_its_template_is_quarantined(self):
        data = dataset({('lead_mngt', 'report_question'): [
            row('lead_mngt', 'report_question', id=1, setup_id=404, question_output='Area')]})
        report = synchronize(FakeSource(data))
        self.assertEqual(report['lead_mngt.report_question']['quarantined'], 1)

    def test_sms_timestamps_keep_time_of_day(self):
        from django.utils import timezone as tz
        data = dataset({('lead_mngt', 'sms_log'): [row('lead_mngt', 'sms_log', sms_log_id=1,
                                                       message='Dear customer', send_date='2023-08-05 11:37:25')]})
        synchronize(FakeSource(data))
        sent = tz.localtime(SmsMessage.objects.get().sent_at)
        self.assertEqual((sent.hour, sent.minute, sent.second), (11, 37, 25))


class SourceCorrectionTests(TestCase):
    """A confirmed source error is corrected on every import, with the original kept."""

    def rows(self, gst):
        return dataset({('lead_mngt', 'account_detail'): [
            row('lead_mngt', 'account_detail', account_detail_id=4, bank_id=4, name='Punjab National Bank', gst_no=gst),
            row('lead_mngt', 'account_detail', account_detail_id=2, bank_id=2, name='State Bank of india', gst_no='23AABFO1645E1ZS')]})

    def test_the_wrong_gstin_is_corrected_and_the_original_kept(self):
        from target_core.models import IssuerAccount
        synchronize(FakeSource(self.rows('23AAACP0165G1ZX')))
        self.assertEqual(IssuerAccount.objects.get(code=4).gst_number, '23AABFO1645E1ZS')
        staged = SourceRow.objects.get(table='account_detail', key=source_key(4))
        self.assertEqual(staged.payload['gst_no'], '23AAACP0165G1ZX')             # evidence retained
        self.assertTrue(any('corrected from 23AAACP0165G1ZX' in p for p in staged.problems))

    def test_the_correction_is_stable_on_repeat(self):
        synchronize(FakeSource(self.rows('23AAACP0165G1ZX')))
        report = synchronize(FakeSource(self.rows('23AAACP0165G1ZX')))
        self.assertEqual(report['lead_mngt.account_detail']['updated'], 0)

    def test_a_value_fixed_at_source_is_not_overwritten(self):
        from target_core.models import IssuerAccount
        synchronize(FakeSource(self.rows('23AABFO9999X1Z1')))
        self.assertEqual(IssuerAccount.objects.get(code=4).gst_number, '23AABFO9999X1Z1')

    def test_other_rows_are_untouched(self):
        from target_core.models import IssuerAccount
        synchronize(FakeSource(self.rows('23AAACP0165G1ZX')))
        staged = SourceRow.objects.get(table='account_detail', key=source_key(2))
        self.assertFalse(staged.problems)
