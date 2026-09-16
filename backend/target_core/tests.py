from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
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
