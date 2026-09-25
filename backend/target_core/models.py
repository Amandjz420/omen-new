"""Compatibility registry. Edit model definitions in apps/<domain>/models.py.

The target_core app label, tables, permissions and migration graph stay stable.
"""
from apps.common.models import Entity, NamedEntity
from apps.accounts.models import LegacyProject, RoleDefinition, LegacyAccount, RoleAssignment, LoginEvent
from apps.organization.models import Employee, SalaryBaseline, SalaryBaselineComponent, SalaryResult, LeaveOpeningBalance, LeadDivision, LeadSubdivision, EmployeeTarget, EmployeeAssignmentRule
from apps.directory.models import Bank, BankBranch, ClientType, ClientOffice, ContactDesignation, Contact
from apps.catalog.models import ServiceType, ServiceSubtype, State, District, Region, Circle, Block, Panchayat, Village, City, Location, SubLocation, AdministrativeDivision, OfficialLocation, IfscArea, ScrutinyRequirement, ReportUsage
from apps.leads.models import Lead, RequestedService, Borrower, Case, LeadNote, FollowUp, LeadParty, LeadAttachment
from apps.workorders.models import WorkOrder, WorkOrderRevision
from apps.valuations.models import Valuation, QuestionCategory, Question, QuestionOption, ValuationAnswer, ValuationVerification, Reversion, ValuationAttachment, ValuationEvent
from apps.reports.models import BankReport, ReportTemplate, ReportHeading, ReportTemplateLine
from apps.billing.models import ChargeType, ValuationCharge, Invoice, InvoiceLine, Receipt, ReceiptAllocation, InvoiceFollowUp, IssuerAccount, FeeRule, CreditNote
from apps.documents.models import Document, UploadConfiguration, DocumentUsage
from apps.dispatch.models import Dispatch, DispatchItem, SmsMessage
from apps.migration_pipeline.models import ImportBatch, SourceIdentity, MigrationIssue, SourceRow
from apps.audit.models import LocalRecord, IntakeAudit, LeadCounter
