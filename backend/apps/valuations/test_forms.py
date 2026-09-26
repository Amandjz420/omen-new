"""The valuation form: queue, opening, sections, every answer type, scope, and
the importer's handling of an edited imported valuation."""
import datetime
import uuid

from django.contrib.auth.models import User
from django.test import TestCase

from target_core import models as m
from target_core.sync import source_key, synchronize
from apps.migration_pipeline.tests import FakeSource, dataset, row


class Form:
    """A small form: two sections, one question of every answer type."""

    def build(self):
        self.service = m.ServiceType.objects.create(name='Valuation of asset')
        self.subtype = m.ServiceSubtype.objects.create(name='L & B', service=self.service)
        self.site = m.QuestionCategory.objects.create(name='Site', source_sequence=2)
        self.value = m.QuestionCategory.objects.create(name='Valuation', source_sequence=5)

        def q(text, kind, category, seq, mandatory=False, track=1):
            return m.Question.objects.create(service=self.service, subtype=self.subtype, category=category,
                                             text=text, answer_type=kind, question_type=track,
                                             is_mandatory=mandatory, legacy_status='1', legacy_deleted='0',
                                             source_sequence=seq)

        def opts(question, *labels, columns=None):
            return [m.QuestionOption.objects.create(question=question, value=label, source_sequence=n,
                                                    value_type=(columns[n] if columns else ''), legacy_deleted='0')
                    for n, label in enumerate(labels)]

        self.radio = q('Is it land locked', 1, self.site, 10, mandatory=True)
        self.radio_opts = opts(self.radio, 'Yes', 'No')
        self.check = q('Documents produced', 2, self.site, 11)
        self.check_opts = opts(self.check, 'Khatoni', 'Search report', 'Map')
        self.text = q('Year of construction', 3, self.site, 12, mandatory=True)
        self.grid = q('Name of the owner', 4, self.site, 13)
        self.grid_opts = opts(self.grid, 'Name', 'Share')
        self.total = q('Total abstract', 5, self.value, 20)
        self.total_opts = opts(self.total, 'Land', 'Building')
        self.calc = q('Details of valuation', 6, self.value, 21)
        self.calc_opts = opts(self.calc, 'Item', 'Plinth area', 'Rate', 'Depreciation', 'Net value',
                              columns=['', 'A', 'B', 'C', 'D'])

    def lead_with_case(self, assigned=None, ordered=True):
        office = m.ClientOffice.objects.create(name='SBI Main')
        lead = m.Lead.objects.create(office=office, date_basis='actual_intake', legacy_status='4', legacy_deleted='0',
                                     number=f'L-{uuid.uuid4().hex[:8]}', assigned_employee=assigned,
                                     received_date=datetime.date(2026, 9, 20))
        borrower = m.Borrower.objects.create(lead=lead, name='Asha Verma', legacy_deleted='0')
        case = m.Case.objects.create(lead=lead, borrower=borrower, service=self.service, subtype=self.subtype)
        if ordered:
            m.WorkOrder.objects.create(lead=lead, borrower=borrower, number=f'O-{uuid.uuid4().hex[:8]}')
        return case


class ValuationFormTests(Form, TestCase):
    def setUp(self):
        self.build()
        self.user = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(self.user)
        self.case = self.lead_with_case()

    def open(self, case=None):
        return self.client.post(f'/api/valuations/cases/{(case or self.case).pk}/', {}, content_type='application/json')

    def put(self, valuation_id, key, answers):
        return self.client.put(f'/api/valuations/{valuation_id}/sections/{key}/', {'answers': answers},
                               content_type='application/json')

    # --- opening -----------------------------------------------------------
    def test_opening_a_case_creates_one_pending_valuation(self):
        first = self.open()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()['status'], 'Pending')
        again = self.open()
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()['id'], first.json()['id'])
        self.assertEqual(m.Valuation.objects.filter(case=self.case).count(), 1)

    def test_a_case_without_a_work_order_cannot_be_valued(self):
        response = self.open(self.lead_with_case(ordered=False))
        self.assertEqual(response.status_code, 409)
        self.assertIn('work order', response.json()['error'])

    # --- sections ----------------------------------------------------------
    def test_sections_follow_legacy_order_and_report_progress(self):
        v = self.open().json()
        self.assertEqual([s['name'] for s in v['sections']], ['Site', 'Valuation'])
        site = v['sections'][0]
        self.assertEqual((site['questions'], site['answered'], site['required'], site['required_answered']),
                         (4, 0, 2, 0))

    def test_grid_columns_keep_legacy_order(self):
        v = self.open().json()
        body = self.client.get(f"/api/valuations/{v['id']}/sections/{self.value.pk}/").json()
        calc = next(q for q in body['questions'] if q['id'] == str(self.calc.pk))
        self.assertEqual([o['column'] for o in calc['options']], ['', 'A', 'B', 'C', 'D'])

    # --- every answer type -------------------------------------------------
    def test_every_answer_type_saves_and_reads_back(self):
        v = self.open().json()
        site = self.put(v['id'], str(self.site.pk), [
            {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[1].pk)]},
            {'question': str(self.check.pk), 'selected': [str(self.check_opts[0].pk), str(self.check_opts[2].pk)]},
            {'question': str(self.text.pk), 'value': '1999'},
            {'question': str(self.grid.pk), 'rows': [
                {'cells': {str(self.grid_opts[0].pk): 'Mr. Tiwari', str(self.grid_opts[1].pk): '50%'}},
                {'cells': {str(self.grid_opts[0].pk): 'Mrs. Tiwari', str(self.grid_opts[1].pk): '50%'}}]}])
        self.assertEqual(site.status_code, 200, site.content)
        answers = {q['id']: q['answer'] for q in site.json()['questions']}
        self.assertEqual(answers[str(self.radio.pk)]['selected'], [str(self.radio_opts[1].pk)])
        self.assertEqual(len(answers[str(self.check.pk)]['selected']), 2)
        self.assertEqual(answers[str(self.text.pk)]['value'], '1999')
        self.assertEqual([r['group'] for r in answers[str(self.grid.pk)]['rows']], [1, 2])
        # the chosen option's text is stored as its value, as in the legacy data
        self.assertEqual(m.ValuationAnswer.objects.get(question=self.radio).value, 'No')
        progress = site.json()['sections'][0]
        self.assertEqual((progress['answered'], progress['required_answered']), (4, 2))

    def test_a_sum_question_reports_its_total(self):
        v = self.open().json()
        body = self.put(v['id'], str(self.value.pk), [{'question': str(self.total.pk), 'values': {
            str(self.total_opts[0].pk): '11.15', str(self.total_opts[1].pk): '20'}}]).json()
        total = next(q for q in body['questions'] if q['id'] == str(self.total.pk))
        self.assertAlmostEqual(total['answer']['total'], 31.15)

    def test_the_formula_column_is_computed_on_the_server(self):
        v = self.open().json()
        a, b, c, d = (str(o.pk) for o in self.calc_opts[1:])
        body = self.put(v['id'], str(self.value.pk), [{'question': str(self.calc.pk), 'rows': [
            {'cells': {a: '223.05', b: '4500', c: '30.59', d: 'whatever the browser sent'}}]}]).json()
        calc = next(q for q in body['questions'] if q['id'] == str(self.calc.pk))
        # Math.round((223.05 x 4500) x (1 - 30.59/100)) = Math.round(696685.52...) = 696686
        self.assertEqual(calc['answer']['rows'][0]['cells'][d], '696686')

    def test_the_formula_rounds_halves_up_like_the_legacy_page(self):
        from target_core.valuations import js_round
        self.assertEqual((js_round(2.5), js_round(3.5), js_round(-2.5)), (3, 4, -2))   # Math.round semantics

    def test_saving_one_question_leaves_the_others_untouched(self):
        v = self.open().json()
        self.put(v['id'], str(self.site.pk), [{'question': str(self.text.pk), 'value': '1999'},
                                             {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[0].pk)]}])
        self.put(v['id'], str(self.site.pk), [{'question': str(self.text.pk), 'value': '2001'}])
        self.assertTrue(m.ValuationAnswer.objects.filter(question=self.radio).exists())
        self.assertEqual(m.ValuationAnswer.objects.get(question=self.text).value, '2001')

    def test_clearing_an_answer_removes_it(self):
        v = self.open().json()
        self.put(v['id'], str(self.site.pk), [{'question': str(self.text.pk), 'value': '1999'}])
        self.put(v['id'], str(self.site.pk), [{'question': str(self.text.pk), 'value': ''}])
        self.assertFalse(m.ValuationAnswer.objects.filter(question=self.text).exists())

    # --- refusals ----------------------------------------------------------
    def test_two_choices_for_a_single_choice_question_are_refused(self):
        v = self.open().json()
        response = self.put(v['id'], str(self.site.pk), [{'question': str(self.radio.pk),
                                                          'selected': [str(o.pk) for o in self.radio_opts]}])
        self.assertEqual(response.status_code, 400)

    def test_an_option_from_another_question_is_refused(self):
        v = self.open().json()
        response = self.put(v['id'], str(self.site.pk), [{'question': str(self.radio.pk),
                                                          'selected': [str(self.check_opts[0].pk)]}])
        self.assertEqual(response.status_code, 400)

    def test_a_question_from_another_section_is_refused(self):
        v = self.open().json()
        response = self.put(v['id'], str(self.site.pk), [{'question': str(self.calc.pk), 'rows': []}])
        self.assertEqual(response.status_code, 400)

    def test_a_submitted_valuation_cannot_be_edited(self):
        v = self.open().json()
        m.Valuation.objects.filter(pk=v['id']).update(legacy_status='Submit')
        response = self.put(v['id'], str(self.site.pk), [{'question': str(self.text.pk), 'value': '1999'}])
        self.assertEqual(response.status_code, 409)

    def test_a_retired_question_that_was_answered_stays_visible(self):
        v = self.open().json()
        self.put(v['id'], str(self.site.pk), [{'question': str(self.text.pk), 'value': '1999'}])
        m.Question.objects.filter(pk=self.text.pk).update(legacy_deleted='1')
        body = self.client.get(f"/api/valuations/{v['id']}/sections/{self.site.pk}/").json()
        retired = next(q for q in body['questions'] if q['id'] == str(self.text.pk))
        self.assertTrue(retired['retired'])
        self.assertEqual(retired['answer']['value'], '1999')

    # --- queue -------------------------------------------------------------
    def test_the_queue_lists_ordered_cases_and_hides_cancelled_work(self):
        self.lead_with_case(ordered=False)
        cancelled = self.lead_with_case()
        m.Valuation.objects.create(case=cancelled, legacy_status='Cancel')
        default = self.client.get('/api/valuations/').json()
        self.assertEqual(default['total'], 1)
        self.assertIsNone(default['results'][0]['valuation'])
        self.assertEqual(self.client.get('/api/valuations/?status=Cancel').json()['total'], 1)
        self.assertEqual(self.client.get('/api/valuations/?status=not_started').json()['total'], 1)


def user_with_role(source_id, employee):
    """A signed-in-capable user holding one LEAD role, identified by its legacy id."""
    import uuid
    lead_project = m.LegacyProject.objects.get_or_create(name='LEAD')[0]
    # One role per legacy id, reused, so a test may create several users holding it.
    identity = m.SourceIdentity.objects.filter(environment='main', schema='uam_user', table='usertype',
                                               key=source_key(source_id)).first()
    if identity:
        role = m.RoleDefinition.objects.get(pk=identity.target_id)
    else:
        role = m.RoleDefinition.objects.create(name=f'role {source_id}', project=lead_project,
                                               legacy_status='1', legacy_deleted='0')
        m.SourceIdentity.objects.create(batch=m.ImportBatch.objects.create(), environment='main', schema='uam_user',
                                        table='usertype', key=source_key(source_id),
                                        target_model='target_core.RoleDefinition', target_id=role.pk)
    login = f'u{source_id}-{uuid.uuid4().hex[:6]}'
    user = User.objects.create_user(login, password='x', is_staff=True)
    account = m.LegacyAccount.objects.create(name='A', login_id=login, user=user, employee=employee,
                                             legacy_status='1', must_change_password=False)
    m.RoleAssignment.objects.create(account=account, role=role, project=lead_project,
                                    legacy_status='1', legacy_deleted='0')
    return user


class AssessorScopeTests(Form, TestCase):
    """Field Assessors and LMS Valuators see only leads assigned to them."""

    def setUp(self):
        self.build()
        self.me = m.Employee.objects.create(name='Assessor')
        self.other = m.Employee.objects.create(name='Someone else')
        self.mine = self.lead_with_case(assigned=self.me)
        self.theirs = self.lead_with_case(assigned=self.other)

    def user_with_role(self, source_id, employee):
        return user_with_role(source_id, employee)

    def test_a_field_assessor_sees_only_their_own_leads(self):
        self.client.force_login(self.user_with_role('157', self.me))
        rows = self.client.get('/api/valuations/').json()
        self.assertTrue(rows['scoped'])
        self.assertEqual([r['case'] for r in rows['results']], [str(self.mine.pk)])

    def test_an_lms_valuator_is_scoped_the_same_way(self):
        self.client.force_login(self.user_with_role('159', self.me))
        self.assertEqual(self.client.get('/api/valuations/').json()['total'], 1)

    def test_a_scoped_user_cannot_open_another_assessors_case(self):
        self.client.force_login(self.user_with_role('157', self.me))
        response = self.client.post(f'/api/valuations/cases/{self.theirs.pk}/', {}, content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_a_scoped_user_cannot_read_another_assessors_valuation(self):
        valuation = m.Valuation.objects.create(case=self.theirs, legacy_status='Pending')
        self.client.force_login(self.user_with_role('157', self.me))
        self.assertEqual(self.client.get(f'/api/valuations/{valuation.pk}/').status_code, 404)

    def test_other_roles_see_every_lead(self):
        self.client.force_login(self.user_with_role('145', self.me))   # Administrator
        rows = self.client.get('/api/valuations/').json()
        self.assertFalse(rows['scoped'])
        self.assertEqual(rows['total'], 2)

    def test_a_scoped_user_with_no_employee_sees_nothing(self):
        self.client.force_login(self.user_with_role('157', None))
        self.assertEqual(self.client.get('/api/valuations/').json()['total'], 0)


class ImportedValuationEditTests(TestCase):
    """Editing an imported valuation, then re-importing, must neither abort the
    import nor revert the edit."""

    def test_reimport_after_editing_an_imported_valuation(self):
        data = dataset({
            ('lead_mngt', 'lead_order'): [row('lead_mngt', 'lead_order', lead_order_id=1, lead_id=1, lead_borrower_id=1)],
            ('lead_mngt', 'valuation'): [row('lead_mngt', 'valuation', valuation_id=1, client_customer_id=1,
                                             lead_order_id=1, valuation_status='Revert')],
            ('lead_mngt', 'question'): [row('lead_mngt', 'question', question_id=1, question='Year of construction',
                                            answer_type=3, service_type=1, service_sub_type=1,
                                            status='1', delete_status='0')],
            ('lead_mngt', 'valuation_answer'): [row('lead_mngt', 'valuation_answer', answer_id=1, valuation_id=1,
                                                    question_id=1, answer_group=0, value='1995')]})
        synchronize(FakeSource(data))
        valuation = m.Valuation.objects.get()
        self.assertEqual(m.ValuationAnswer.objects.get().value, '1995')

        user = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(user)
        question = m.Question.objects.get()
        key = str(question.category_id) if question.category_id else 'none'
        response = self.client.put(f'/api/valuations/{valuation.pk}/sections/{key}/',
                                   {'answers': [{'question': str(question.pk), 'value': '1999'}]},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(m.LocalRecord.objects.filter(target_id=valuation.pk).exists())

        # The imported answer row was replaced, leaving its source identity
        # pointing at nothing. Before PARENT_OWNED this aborted the import.
        report = synchronize(FakeSource(data))
        self.assertEqual(report['lead_mngt.valuation_answer']['inserted'], 0)
        self.assertEqual(m.ValuationAnswer.objects.get().value, '1999')
        staged = m.SourceRow.objects.get(table='valuation_answer')
        self.assertEqual(staged.payload['value'], '1995')     # source evidence retained


class ScopeFailsSafeTests(Form, TestCase):
    """Review finding G7: losing a grant must never widen access."""

    def setUp(self):
        self.build()
        self.me = m.Employee.objects.create(name='Assessor')
        self.other = m.Employee.objects.create(name='Someone else')
        self.mine = self.lead_with_case(assigned=self.me)
        self.theirs = self.lead_with_case(assigned=self.other)
        self.theirs_valuation = m.Valuation.objects.create(case=self.theirs, legacy_status='Pending')

    def read_theirs(self):
        return self.client.get(f'/api/valuations/{self.theirs_valuation.pk}/').status_code

    def test_deactivating_the_only_grant_does_not_widen_access(self):
        user = user_with_role('157', self.me)
        self.client.force_login(user)
        self.assertEqual(self.read_theirs(), 404)
        m.RoleAssignment.objects.filter(account__user=user).update(legacy_status='0')
        self.assertEqual(self.read_theirs(), 404)                  # the same session; previously 200
        self.assertEqual(self.client.get('/api/valuations/').json()['total'], 0)

    def test_a_grant_whose_role_is_disabled_does_not_count(self):
        user = user_with_role('145', self.me)                       # a broad role
        self.client.force_login(user)
        self.assertEqual(self.read_theirs(), 200)
        held = m.RoleAssignment.objects.filter(account__user=user).values('role')
        m.RoleDefinition.objects.filter(pk__in=held).update(legacy_status='0')
        self.assertEqual(self.read_theirs(), 404)

    def test_a_valid_broad_role_keeps_full_access(self):
        self.client.force_login(user_with_role('145', self.me))
        self.assertEqual(self.client.get('/api/valuations/').json()['total'], 2)


class HistoricalAnswerTests(Form, TestCase):
    """Review finding G2: reading and saving must not rewrite historical answers."""

    def setUp(self):
        self.build()
        self.client.force_login(User.objects.create_user('staff', password='x', is_staff=True))
        case = self.lead_with_case()
        self.v = self.client.post(f'/api/valuations/cases/{case.pk}/', {}, content_type='application/json').json()['id']
        self.name, self.share = self.grid_opts

    def store(self, option, group, value, document=None):
        return m.ValuationAnswer.objects.create(valuation_id=self.v, question=self.grid, option=option,
                                                answer_group=group, value=value, document=document)

    def section(self):
        return self.client.get(f'/api/valuations/{self.v}/sections/{self.site.pk}/').json()

    def grid_of(self, body):
        return next(q for q in body['questions'] if q['id'] == str(self.grid.pk))

    def put(self, answers):
        return self.client.put(f'/api/valuations/{self.v}/sections/{self.site.pk}/', {'answers': answers},
                               content_type='application/json')

    def stored(self):
        return sorted((str(a.option_id), a.answer_group, a.value)
                      for a in m.ValuationAnswer.objects.filter(valuation_id=self.v, question=self.grid))

    def test_codex_reproduction_duplicate_cell_survives_an_unchanged_save(self):
        self.store(self.name, 7, 'Mr. Tiwari')
        self.store(self.name, 7, 'Mrs. Tiwari')
        before = self.stored()
        grid = self.grid_of(self.section())
        self.assertEqual(len(grid['conflicts']), 1)                        # reported, not hidden
        self.assertEqual(self.put([{'question': grid['id'], **grid['answer']}]).status_code, 200)
        self.assertEqual(self.stored(), before)                            # previously one answer, in group 1

    def test_an_unchanged_whole_section_round_trip_writes_nothing(self):
        self.store(self.name, 7, 'Mr. Tiwari')
        self.store(self.share, 9, '50%')
        ids = set(m.ValuationAnswer.objects.values_list('id', flat=True))
        body = self.section()
        self.assertEqual(self.put([{'question': q['id'], **q['answer']} for q in body['questions']]).status_code, 200)
        self.assertEqual(set(m.ValuationAnswer.objects.values_list('id', flat=True)), ids)
        self.assertFalse(m.IntakeAudit.objects.filter(action='change_valuation_answers').exists())

    def test_editing_one_row_keeps_group_numbers_and_documents(self):
        deed = m.Document.objects.create(storage_provider='local', storage_key='x', original_name='deed.pdf')
        kept = self.store(self.name, 7, 'Mr. Tiwari', document=deed)
        self.store(self.name, 9, 'Mrs. Tiwari')
        grid = self.grid_of(self.section())
        rows = grid['answer']['rows']
        rows[1]['cells'][str(self.name.pk)] = 'Mrs. Sharma'                  # edit group 9 only
        self.assertEqual(self.put([{'question': grid['id'], 'rows': rows}]).status_code, 200)
        self.assertEqual(self.stored(), [(str(self.name.pk), 7, 'Mr. Tiwari'), (str(self.name.pk), 9, 'Mrs. Sharma')])
        kept.refresh_from_db()
        self.assertEqual(kept.document_id, deed.pk)                         # same row, document intact

    def test_a_new_row_takes_the_next_free_group(self):
        self.store(self.name, 7, 'Mr. Tiwari')
        grid = self.grid_of(self.section())
        rows = grid['answer']['rows'] + [{'cells': {str(self.name.pk): 'New owner'}}]
        self.put([{'question': grid['id'], 'rows': rows}])
        self.assertIn((str(self.name.pk), 8, 'New owner'), self.stored())

    def test_changing_a_conflicting_cell_needs_confirmation_and_is_evidenced(self):
        self.store(self.name, 7, 'Mr. Tiwari')
        self.store(self.name, 7, 'Mrs. Tiwari')
        grid = self.grid_of(self.section())
        rows = grid['answer']['rows']
        rows[0]['cells'][str(self.name.pk)] = 'Resolved owner'
        refused = self.put([{'question': grid['id'], 'rows': rows}])
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(len(self.stored()), 2)                             # nothing merged
        self.assertEqual(self.put([{'question': grid['id'], 'rows': rows, 'resolve': True}]).status_code, 200)
        self.assertEqual(self.stored(), [(str(self.name.pk), 7, 'Resolved owner')])
        audit = m.IntakeAudit.objects.get(action='change_valuation_answers')
        self.assertEqual(sorted(r[2] for r in audit.before[str(self.grid.pk)]), ['Mr. Tiwari', 'Mrs. Tiwari'])

    def test_two_rows_cannot_claim_one_group(self):
        grid = self.grid_of(self.section())
        rows = [{'group': 3, 'cells': {str(self.name.pk): 'A'}}, {'group': 3, 'cells': {str(self.name.pk): 'B'}}]
        self.assertEqual(self.put([{'question': grid['id'], 'rows': rows}]).status_code, 400)
