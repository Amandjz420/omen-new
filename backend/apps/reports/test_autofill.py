"""Prefilling the bank report's assessed values from the valuation's answers."""
from decimal import Decimal

from django.test import SimpleTestCase

from target_core import models as m
from apps.reports.autofill import amount, field_for, from_rows
from apps.reports.test_reports import BankReportTests


class Reading(SimpleTestCase):
    def test_labels(self):
        self.assertEqual(field_for('Fair Market Value (FMV)'), 'market_fair_amount')
        self.assertEqual(field_for('Present Market Value'), 'market_fair_amount')
        self.assertEqual(field_for('Net Realizable Value'), 'realisable_value_amount')
        self.assertEqual(field_for('ERV'), 'realisable_value_amount')
        self.assertEqual(field_for('Forced /Distress Sales Value'), 'distress_value_amount')
        self.assertIsNone(field_for('Fair market Value after Completion of Flat/ Shop'))
        self.assertIsNone(field_for('Any negative factors which affect the market value?'))

    def test_figures(self):
        self.assertEqual(amount('Rs. 25,00,000/-'), Decimal('2500000'))
        self.assertEqual(amount('45.5 lakh'), Decimal('4550000'))
        self.assertEqual(amount('1.2 Cr'), Decimal('12000000'))
        self.assertIsNone(amount('Not applicable'))

    def test_a_table_is_preferred_and_earlier_valuations_ignored(self):
        questions = [(1, 'Was property valued earlier', 'grid', [(11, 'Market value')]),
                     (2, 'Fair Market Value of immovable property', 'text', []),
                     (3, 'Other Market Value', 'grid', [(31, 'FMV'), (32, 'ERV'), (33, 'DSV')])]
        answers = {1: [(11, 1, '900000')], 2: [(None, 0, 'Rs. 40,00,000')],
                   3: [(31, 1, '3850000'), (32, 1, '3500000'), (33, 1, '3000000')]}
        values, sources = from_rows(questions, answers)
        self.assertEqual(values, {'market_fair_amount': Decimal('3850000'), 'realisable_value_amount': Decimal('3500000'),
                                  'distress_value_amount': Decimal('3000000')})
        self.assertEqual(sources['market_fair_amount'], 'Other Market Value')


class Prefill(BankReportTests):
    def test_the_report_form_starts_from_the_valuations_figures(self):
        table = m.Question.objects.create(service=self.service, subtype=self.subtype, category=self.value,
                                          text='Other Market Value', answer_type=4, question_type=2,
                                          legacy_status='1', legacy_deleted='0', source_sequence=30)
        fmv, erv, dsv = (m.QuestionOption.objects.create(question=table, value=v, source_sequence=n, legacy_deleted='0')
                         for n, v in enumerate(('FMV', 'ERV', 'DSV')))
        for option, value in ((fmv, '38,50,000'), (erv, '35,00,000'), (dsv, '30,00,000')):
            m.ValuationAnswer.objects.create(valuation_id=self.v, question=table, option=option, answer_group=1, value=value)
        body = self.client.get(f'/api/bank-reports/{self.v}/').json()
        self.assertEqual((body['values']['market_fair_amount'], body['values']['realisable_value_amount'],
                          body['values']['distress_value_amount']), ('3850000.00', '3500000.00', '3000000.00'))
        self.assertEqual(body['prefilled_from']['market_fair_amount'], 'Other Market Value')
        self.assertEqual(body['bank_name'], 'State Bank of India')
        self.assertEqual(body['branch_name'], 'Main Branch Itarsi')
