"""Valuation billing, photos and answer documents."""
import io
import shutil
import tempfile
import zipfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from . import models as m
from .sync import source_key, synchronize
from .test_valuations import Form
from .tests import FakeSource, dataset, row

MEDIA = tempfile.mkdtemp(prefix='omen-test-media-')
JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 64
PDF = b'%PDF-1.7\n' + b'\x00' * 64


def docx():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('word/document.xml', '<w:document/>')
    return buffer.getvalue()


def archive():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('invoice.exe', 'MZ')
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class Extras(Form, TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.build()
        batch = m.ImportBatch.objects.create()
        self.heads = {}
        for sid, name in [('1', 'Professional charges\t\t'), ('2', 'Discount (if any)\t\t\t'),
                          ('3', 'Photo charges'), ('6', 'Delivery / Courier Charges')]:
            head = m.ChargeType.objects.create(name=name, legacy_status='1', legacy_deleted='0', source_sequence=int(sid))
            m.SourceIdentity.objects.create(batch=batch, environment='main', schema='lead_mngt', table='billing_head',
                                            key=source_key(sid), target_model='target_core.ChargeType', target_id=head.pk)
            self.heads[sid] = head
        self.docs = m.Question.objects.create(service=self.service, subtype=self.subtype, category=self.site,
                                              text='Documents produced for perusal', answer_type=2, is_document=True,
                                              legacy_status='1', legacy_deleted='0', source_sequence=14)
        self.deed = m.QuestionOption.objects.create(question=self.docs, value='Sale deed', source_sequence=0, legacy_deleted='0')
        self.map = m.QuestionOption.objects.create(question=self.docs, value='Map', source_sequence=1, legacy_deleted='0')
        self.user = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(self.user)
        case = self.lead_with_case()
        self.v = self.client.post(f'/api/valuations/cases/{case.pk}/', {}, content_type='application/json').json()['id']

    # --- helpers -----------------------------------------------------------
    def bill(self, lines, advance='0'):
        return self.client.put(f'/api/valuations/{self.v}/billing/', {
            'lines': [{'charge_type': str(self.heads[k].pk), 'amount': a} for k, a in lines.items()],
            'advance': advance}, content_type='application/json')

    def upload_photo(self, content=JPEG, kind='1', name='front.jpg'):
        return self.client.post(f'/api/valuations/{self.v}/photos/',
                                {'type': kind, 'file': SimpleUploadedFile(name, content)})

    def choose_documents(self, *options):
        return self.client.put(f'/api/valuations/{self.v}/sections/{self.site.pk}/', {'answers': [
            {'question': str(self.docs.pk), 'selected': [str(o.pk) for o in options]}]}, content_type='application/json')

    def attach(self, option, content=PDF, name='deed.pdf'):
        return self.client.post(f'/api/valuations/{self.v}/documents/', {
            'question': str(self.docs.pk), 'option': str(option.pk), 'file': SimpleUploadedFile(name, content)})


class BillingTests(Extras):
    def test_totals_are_computed_on_the_server(self):
        body = self.bill({'1': '2000', '3': '500', '6': '100', '2': '300'}, advance='1000').json()
        t = body['totals']
        self.assertEqual((t['charges'], t['discount'], t['total']), ('2600.00', '300.00', '2300.00'))
        self.assertEqual((t['gst'], t['after_tax'], t['remaining']), ('414.00', '2714.00', '1714.00'))
        v = m.Valuation.objects.get(pk=self.v)
        self.assertEqual((v.total_billing_amount, v.total_after_tax, v.remaining_amount),
                         (Decimal('2300.00'), Decimal('2714.00'), Decimal('1714.00')))

    def test_a_discount_reduces_the_bill_however_it_is_typed(self):
        positive = self.bill({'1': '1000', '2': '100'}).json()['totals']['total']
        negative = self.bill({'1': '1000', '2': '-100'}).json()['totals']['total']
        self.assertEqual((positive, negative), ('900.00', '900.00'))
        self.assertEqual(m.ValuationCharge.objects.get(charge_type=self.heads['2']).amount, Decimal('-100.00'))

    def test_money_is_exact_to_the_paisa(self):
        # 3365 x 1.18 is 3970.70; binary floating point gives 3970.6999...
        self.assertEqual(self.bill({'1': '3365'}).json()['totals']['after_tax'], '3970.70')

    def test_a_negative_charge_is_refused(self):
        self.assertEqual(self.bill({'1': '-50'}).status_code, 400)

    def test_a_discount_larger_than_the_charges_is_refused(self):
        self.assertEqual(self.bill({'1': '100', '2': '500'}).status_code, 400)

    def test_a_negative_advance_is_refused(self):
        self.assertEqual(self.bill({'1': '100'}, advance='-1').status_code, 400)

    def test_an_invoiced_valuation_cannot_have_its_charges_changed(self):
        m.Invoice.objects.create(valuation_id=self.v, number='INV-1')
        response = self.bill({'1': '100'})
        self.assertEqual(response.status_code, 409)
        self.assertIn('invoiced', response.json()['error'])
        self.assertFalse(self.client.get(f'/api/valuations/{self.v}/billing/').json()['editable'])

    def test_a_submitted_valuation_cannot_be_billed(self):
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Submit')
        self.assertEqual(self.bill({'1': '100'}).status_code, 409)

    def test_every_current_head_is_listed_with_the_discount_marked(self):
        lines = self.client.get(f'/api/valuations/{self.v}/billing/').json()['lines']
        self.assertEqual([l['name'] for l in lines][:2], ['Professional charges', 'Discount (if any)'])
        self.assertEqual([l['discount'] for l in lines], [False, True, False, False])


class PhotoTests(Extras):
    def test_a_photo_is_stored_listed_and_served_safely(self):
        body = self.upload_photo().json()
        self.assertEqual(body['photos'][0]['type_label'], 'Front')
        self.assertNotIn('Front', body['missing'])
        self.assertIn('Site Plan', body['missing'])
        served = self.client.get(f"/api/valuations/{self.v}/photos/{body['photos'][0]['id']}/file/")
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(b''.join(served.streaming_content), JPEG)

    def test_a_non_image_renamed_as_a_photo_is_refused(self):
        response = self.upload_photo(content=b'<html><script>alert(1)</script>', name='front.jpg')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(m.Document.objects.exists())

    def test_an_unknown_photo_type_is_refused(self):
        self.assertEqual(self.upload_photo(kind='99').status_code, 400)

    def test_an_oversized_photo_is_refused(self):
        from . import files
        original = files.MAX_BYTES
        files.MAX_BYTES = 10
        try:
            self.assertEqual(self.upload_photo().status_code, 400)
        finally:
            files.MAX_BYTES = original

    def test_removing_a_photo_keeps_the_file_as_evidence(self):
        photo_id = self.upload_photo().json()['photos'][0]['id']
        self.client.delete(f'/api/valuations/{self.v}/photos/{photo_id}/')
        self.assertFalse(m.ValuationAttachment.objects.exists())
        self.assertEqual(m.Document.objects.count(), 1)

    def test_a_submitted_valuation_takes_no_photos(self):
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Submit')
        self.assertEqual(self.upload_photo().status_code, 409)


class AnswerDocumentTests(Extras):
    def test_a_document_attaches_to_a_chosen_option(self):
        self.choose_documents(self.deed)
        self.assertEqual(self.attach(self.deed).status_code, 201)
        section = self.client.get(f'/api/valuations/{self.v}/sections/{self.site.pk}/').json()
        docs = next(q for q in section['questions'] if q['id'] == str(self.docs.pk))['documents']
        self.assertEqual([(d['option'], d['file']['name']) for d in docs], [(str(self.deed.pk), 'deed.pdf')])

    def test_an_option_must_be_chosen_before_its_document(self):
        self.assertEqual(self.attach(self.deed).status_code, 409)

    def test_word_documents_are_accepted_and_archives_refused(self):
        self.choose_documents(self.deed, self.map)
        self.assertEqual(self.attach(self.deed, docx(), 'deed.docx').status_code, 201)
        self.assertEqual(self.attach(self.map, archive(), 'map.zip').status_code, 400)

    def test_resaving_a_section_keeps_its_attached_documents(self):
        """Regression: answers were deleted and recreated on save, dropping the link."""
        self.choose_documents(self.deed, self.map)
        self.attach(self.deed)
        self.choose_documents(self.deed, self.map)                  # save the section again
        self.assertIsNotNone(m.ValuationAnswer.objects.get(option=self.deed).document_id)

    def test_unchoosing_an_option_removes_its_document_link(self):
        self.choose_documents(self.deed)
        self.attach(self.deed)
        self.choose_documents(self.map)
        self.assertFalse(m.ValuationAnswer.objects.filter(option=self.deed).exists())
        self.assertEqual(m.Document.objects.count(), 1)             # the file itself is kept

    def test_a_document_can_be_detached(self):
        self.choose_documents(self.deed)
        self.attach(self.deed)
        self.client.delete(f'/api/valuations/{self.v}/documents/?question={self.docs.pk}&option={self.deed.pk}')
        self.assertIsNone(m.ValuationAnswer.objects.get(option=self.deed).document_id)

    def test_only_a_document_question_takes_documents(self):
        self.client.put(f'/api/valuations/{self.v}/sections/{self.site.pk}/', {'answers': [
            {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[0].pk)]}]}, content_type='application/json')
        response = self.client.post(f'/api/valuations/{self.v}/documents/', {
            'question': str(self.radio.pk), 'option': str(self.radio_opts[0].pk),
            'file': SimpleUploadedFile('x.pdf', PDF)})
        self.assertEqual(response.status_code, 400)

    def test_a_document_is_served_only_through_its_own_valuation(self):
        self.choose_documents(self.deed)
        doc = self.attach(self.deed).json()['file']['id']
        self.assertEqual(self.client.get(f'/api/valuations/{self.v}/documents/{doc}/file/').status_code, 200)
        other = self.client.post(f'/api/valuations/cases/{self.lead_with_case().pk}/', {},
                                 content_type='application/json').json()['id']
        self.assertEqual(self.client.get(f'/api/valuations/{other}/documents/{doc}/file/').status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA)
class ImportedExtrasEditTests(TestCase):
    """Editing billing and removing a photo on an imported valuation, then
    re-importing, must neither abort the import nor revert the edits."""

    def test_reimport_after_editing_imported_billing_and_photos(self):
        data = dataset({
            ('lead_mngt', 'lead_order'): [row('lead_mngt', 'lead_order', lead_order_id=1, lead_id=1, lead_borrower_id=1)],
            ('lead_mngt', 'valuation'): [row('lead_mngt', 'valuation', valuation_id=1, client_customer_id=1,
                                             lead_order_id=1, valuation_status='Revert')],
            ('lead_mngt', 'billing_head'): [row('lead_mngt', 'billing_head', billing_head_id=1, billing_head_name='Professional',
                                                status='1', delete_status='0')],
            ('lead_mngt', 'valuation_billing'): [row('lead_mngt', 'valuation_billing', billing_id=1, valuation_id=1,
                                                     billing_head_id=1, amount='1000')],
            ('lead_mngt', 'upload'): [row('lead_mngt', 'upload', upload_id=1, doc_path='s3/front.jpg')],
            ('lead_mngt', 'valuation_photo'): [row('lead_mngt', 'valuation_photo', id=1, valuation_id=1,
                                                   upload_id=1, photo_type=1)]})
        synchronize(FakeSource(data))
        valuation = m.Valuation.objects.get()
        head = m.ChargeType.objects.get()
        self.client.force_login(User.objects.create_user('staff', password='x', is_staff=True))
        self.assertEqual(self.client.put(f'/api/valuations/{valuation.pk}/billing/', {
            'lines': [{'charge_type': str(head.pk), 'amount': '1500'}], 'advance': '0'},
            content_type='application/json').status_code, 200)
        photo = m.ValuationAttachment.objects.get()
        self.assertEqual(self.client.delete(f'/api/valuations/{valuation.pk}/photos/{photo.pk}/').status_code, 200)

        report = synchronize(FakeSource(data))          # would have aborted before PARENT_OWNED
        self.assertEqual(report['lead_mngt.valuation_billing']['inserted'], 0)
        self.assertEqual(m.ValuationCharge.objects.get().amount, Decimal('1500.00'))
        self.assertFalse(m.ValuationAttachment.objects.exists())
