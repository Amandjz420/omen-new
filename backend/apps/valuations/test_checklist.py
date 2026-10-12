import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from target_core import models as m
from apps.valuations import deepinfra
from apps.valuations.test_forms import Form, user_with_role


class ChecklistTests(Form, TestCase):
    def setUp(self):
        self.build()
        self.client.force_login(User.objects.create_user('assessor', is_staff=True))
        self.valuation = m.Valuation.objects.create(case=self.lead_with_case(), legacy_status='Pending')
        self.url = f'/api/valuations/{self.valuation.pk}/checklist/'

    def ask(self, **data):
        return self.client.post(self.url + 'follow-up/', data, content_type='application/json')

    def test_matches_submission_gate_and_ignores_blank_optional_and_retired_answers(self):
        m.ValuationAnswer.objects.create(valuation=self.valuation, question=self.text, value='  ')
        other = m.Question.objects.create(service=self.service, subtype=self.subtype, text='Retired',
                                          is_mandatory=True, legacy_deleted='1', legacy_status='1')
        m.ValuationAnswer.objects.create(valuation=self.valuation, question=other, value='')
        check = self.client.get(self.url).json()
        submission = self.client.get(f'/api/valuations/{self.valuation.pk}/submission/').json()
        self.assertEqual(check['missing_required'], submission['missing_required'])
        self.assertEqual({q['question'] for q in check['missing_required']}, {str(self.radio.pk), str(self.text.pk)})

    def test_saving_an_answer_removes_it_from_the_checklist(self):
        response = self.client.put(f'/api/valuations/{self.valuation.pk}/sections/{self.site.pk}/',
            {'answers': [{'question': str(self.text.pk), 'value': '0'}]}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        check = self.client.get(self.url).json()
        self.assertEqual(check['remaining_questions'], 1)
        self.assertEqual(check['missing_required'][0]['question'], str(self.radio.pk))

    def test_photo_upload_closes_only_its_category_and_missing_file_is_flagged(self):
        doc = m.Document.objects.create(storage_provider='local', storage_key='missing.jpg')
        m.ValuationAttachment.objects.create(valuation=self.valuation, document=doc, attachment_type='2')
        with tempfile.TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            self.assertEqual(self.client.get(self.url).json()['photos'][1]['status'], 'unavailable')
            uploaded = self.client.post(f'/api/valuations/{self.valuation.pk}/photos/',
                {'type': '1', 'file': SimpleUploadedFile('front.jpg', b'\xff\xd8\xff\xe0' + b'\0' * 64)})
            self.assertEqual(uploaded.status_code, 201, uploaded.content)
            body = self.client.get(self.url).json()
            self.assertEqual(body['remaining_photos'], 5)
            self.assertEqual(body['photos'][0]['status'], 'recorded')
            self.assertEqual(body['photos'][1]['status'], 'unavailable')

    @mock.patch.object(deepinfra, 'configured', return_value=True)
    @mock.patch.object(deepinfra, 'answer_json', return_value={'prompt': 'In which year was the property constructed?'})
    def test_ai_asks_about_selected_missing_question_without_saving_an_answer(self, model, configured):
        response = self.ask(question=str(self.text.pk))
        self.assertEqual(response.status_code, 200)
        follow = response.json()['follow_up']
        self.assertTrue(follow['ai_generated'])
        self.assertEqual(follow['question'], str(self.text.pk))
        self.assertEqual(follow['section_key'], str(self.site.pk))
        self.assertIn('Year of construction', model.call_args.args[1])
        self.assertIn('"answer_kind": "text"', model.call_args.args[1])
        self.assertFalse(m.ValuationAnswer.objects.filter(valuation=self.valuation).exists())

    @mock.patch.object(deepinfra, 'configured', return_value=True)
    @mock.patch.object(deepinfra, 'answer_json', side_effect=deepinfra.AssistError('Offline'))
    def test_ai_failure_falls_back_to_original_question(self, model, configured):
        body = self.ask(question=str(self.text.pk)).json()['follow_up']
        self.assertFalse(body['ai_generated'])
        self.assertEqual(body['prompt'], 'Please answer: Year of construction')

    @mock.patch.object(deepinfra, 'configured', return_value=False)
    @mock.patch.object(deepinfra, 'answer_json')
    def test_without_ai_the_checklist_and_followup_still_work(self, model, configured):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertFalse(self.ask().json()['follow_up']['ai_generated'])
        model.assert_not_called()

    @mock.patch.object(deepinfra, 'answer_json')
    def test_answered_and_out_of_scope_question_cannot_be_sent_to_ai(self, model):
        m.ValuationAnswer.objects.create(valuation=self.valuation, question=self.text, value='1999')
        self.assertEqual(self.ask(question=str(self.text.pk)).status_code, 409)
        self.assertEqual(self.ask(question=str(self.check.pk)).status_code, 409)
        model.assert_not_called()

    def test_assessor_cannot_read_or_prompt_for_another_cases_checklist(self):
        employee = m.Employee.objects.create(name='Someone else')
        self.client.force_login(user_with_role('157', employee))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.ask().status_code, 404)

    def test_closed_valuation_has_readonly_checklist(self):
        self.valuation.legacy_status = 'Submit'
        self.valuation.save()
        self.assertFalse(self.client.get(self.url).json()['editable'])
        self.assertEqual(self.ask().status_code, 409)
