"""The previous system's files: signing, locating, serving and embedding."""
import datetime
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from target_core import models as m
from apps.documents import s3
from apps.documents.storage import available, file_json, read_bytes, serve
from apps.common.http import IntakeError

AWS = {'AWS_S3_BUCKET_NAME': 'omen-legacy', 'AWS_DEFAULT_REGION': 'ap-south-1',
       'AWS_ACCESS_KEY_ID': 'AKIDEXAMPLE', 'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY'}


class SigningTests(TestCase):
    def test_the_aws_documentation_example(self):
        """Authenticating Requests: Using Query Parameters, whose signature is published."""
        url = s3.presign('test.txt', bucket='examplebucket', region='us-east-1', access_key='AKIAIOSFODNN7EXAMPLE',
                         secret_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', expires=86400,
                         now=datetime.datetime(2013, 5, 24, tzinfo=datetime.timezone.utc), host='examplebucket.s3.amazonaws.com')
        self.assertTrue(url.endswith('X-Amz-Signature=aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404'))

    @mock.patch.dict(os.environ, AWS)
    def test_the_link_names_the_type_and_the_file_and_expires_quickly(self):
        url = s3.presign('LeadUpload/202403_10//photo.jpeg', filename='front "view".jpeg', content_type='image/jpeg')
        self.assertIn('omen-legacy.s3.ap-south-1.amazonaws.com/LeadUpload/202403_10//photo.jpeg?', url)
        self.assertIn('response-content-type=image%2Fjpeg', url)
        self.assertIn('filename%3D%22front%20_view_.jpeg%22', url)             # quotes cannot break the header
        self.assertIn('X-Amz-Expires=300', url)


@mock.patch.dict(os.environ, AWS)
class ServingTests(TestCase):
    def lead_doc(self, key='202403_10//photo_1.jpeg', location='LeadUpload/202403_10//photo_1.jpeg', name='front.jpeg'):
        return m.Document.objects.create(storage_provider='legacy_lead_s3', storage_key=key, original_name=name,
                                         legacy_location=location, legacy_checked_at=datetime.datetime.now(datetime.timezone.utc))

    def test_a_bucket_file_redirects_to_a_signed_link_for_its_verified_key(self):
        response = serve(self.lead_doc(key='202102_14//photo_2.jpeg', location='LeadUpload/202102_14/photo_2.jpeg'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/LeadUpload/202102_14/photo_2.jpeg?', response['Location'])      # the collapsed form, as verified
        self.assertIn('response-content-type=image%2Fjpeg', response['Location'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotIn(AWS['AWS_SECRET_ACCESS_KEY'], response['Location'])

    def test_a_file_that_could_not_be_found_is_unavailable(self):
        doc = self.lead_doc(location='')
        self.assertFalse(available(doc))
        with self.assertRaises(IntakeError) as raised:
            serve(doc)
        self.assertEqual(raised.exception.status, 404)

    def test_without_credentials_the_server_says_so(self):
        doc = self.lead_doc()
        with mock.patch.dict(os.environ, {'AWS_ACCESS_KEY_ID': ''}):
            self.assertFalse(available(doc))
            with self.assertRaises(IntakeError) as raised:
                serve(doc)
        self.assertEqual(raised.exception.status, 503)

    def test_an_unsafe_type_downloads_rather_than_opens(self):
        response = serve(self.lead_doc(key='x/archive.rar', location='LeadUpload/x/archive.rar', name='deeds.rar'))
        self.assertIn('attachment%3B', response['Location'])

    def test_a_user_management_upload_comes_from_the_local_folder(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / '202411').mkdir()
            (Path(root) / '202411' / 'img_67.jpg').write_bytes(b'\xff\xd8\xff\xe0 jpeg')
            doc = m.Document.objects.create(storage_provider='legacy_uam_local', storage_key='202411/img_67.jpg', media_type='image')
            with override_settings(LEGACY_UAM_ROOT=root):
                response = serve(doc)
                self.assertEqual((response.status_code, response['Content-Type']), (200, 'image/jpeg'))   # not "image"
                escape = m.Document.objects.create(storage_provider='legacy_uam_local', storage_key='../../etc/passwd',
                                                   legacy_checked_at=datetime.datetime.now(datetime.timezone.utc))
                self.assertFalse(available(escape))
                with self.assertRaises(IntakeError):
                    serve(escape)

    def test_the_screens_learn_whether_a_file_can_be_opened(self):
        self.assertEqual((file_json(self.lead_doc())['available'], file_json(self.lead_doc())['local']), (True, False))
        self.assertFalse(file_json(self.lead_doc(location=''))['available'])

    def test_an_imported_work_order_letter_opens(self):
        from apps.valuations.test_forms import Form
        form = type('F', (Form, TestCase), {})()
        form.build()
        case = form.lead_with_case()
        order = m.WorkOrder.objects.get(lead=case.lead)
        m.WorkOrder.objects.filter(pk=order.pk).update(document=self.lead_doc(key='order/2207/49.pdf', location='LeadUpload/order/2207/49.pdf', name='49.pdf'))
        self.client.force_login(User.objects.create_user('office', password='x', is_staff=True))
        response = self.client.get(f'/api/work-orders/{order.pk}/document/')
        self.assertEqual(response.status_code, 302)                                   # previously 404: not retrieved
        self.assertIn('response-content-type=application%2Fpdf', response['Location'])

    def test_bank_reports_embed_legacy_photographs(self):
        with mock.patch('urllib.request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'\xff\xd8\xff\xe0 a photo'
            self.assertEqual(read_bytes(self.lead_doc()), b'\xff\xd8\xff\xe0 a photo')
            self.assertIsNone(read_bytes(self.lead_doc(location='')))              # not found: no request is made
        self.assertEqual(urlopen.call_count, 1)


@mock.patch.dict(os.environ, AWS)
class LocatingTests(TestCase):
    def test_each_file_is_recorded_where_it_was_found(self):
        exact = m.Document.objects.create(storage_provider='legacy_lead_s3', storage_key='202403_10//a.jpeg')
        collapsed = m.Document.objects.create(storage_provider='legacy_lead_s3', storage_key='202102_14//b.jpeg')
        gone = m.Document.objects.create(storage_provider='legacy_lead_s3', storage_key='2020/c.pdf')
        with tempfile.TemporaryDirectory() as root:
            Path(root, '202411').mkdir()
            Path(root, '202411', 'd.jpg').write_bytes(b'x')
            uam = m.Document.objects.create(storage_provider='legacy_uam_local', storage_key='202411/d.jpg')
            bucket = {'LeadUpload/': {'LeadUpload/202403_10//a.jpeg', 'LeadUpload/202102_14/b.jpeg'}, 'UAMUpload/': set()}
            with override_settings(LEGACY_UAM_ROOT=root), \
                 mock.patch('apps.documents.management.commands.locate_legacy_files.listing', side_effect=lambda p: bucket[p]):
                call_command('locate_legacy_files', stdout=open(os.devnull, 'w'))
        found = {d.pk: d.legacy_location for d in m.Document.objects.all()}
        self.assertEqual(found[exact.pk], 'LeadUpload/202403_10//a.jpeg')             # kept: the bucket has "//"
        self.assertEqual(found[collapsed.pk], 'LeadUpload/202102_14/b.jpeg')          # collapsed: the bucket has "/"
        self.assertEqual(found[gone.pk], '')
        self.assertEqual(found[uam.pk], 'local:202411/d.jpg')
        self.assertTrue(all(m.Document.objects.values_list('legacy_checked_at', flat=True)))


class EnvironmentTests(TestCase):
    def test_the_env_file_never_overrides_a_variable_already_set(self):
        from config.settings import _load_env
        with tempfile.NamedTemporaryFile('w', suffix='.env', delete=False) as f:
            f.write('# a comment\nOMEN_TEST_A="from file"\nOMEN_TEST_B=from file\n')
        with mock.patch.dict(os.environ, {'OMEN_TEST_B': 'already set'}):
            _load_env(Path(f.name))
            self.assertEqual((os.environ['OMEN_TEST_A'], os.environ['OMEN_TEST_B']), ('from file', 'already set'))
        os.environ.pop('OMEN_TEST_A', None)
        os.unlink(f.name)


@mock.patch.dict(os.environ, AWS)
class ReceiptDocumentTests(TestCase):
    def test_a_legacy_receipt_document_opens_for_those_who_may_see_the_receipt(self):
        doc = m.Document.objects.create(storage_provider='legacy_lead_s3', storage_key='receipt/2021/7.jpg', original_name='7.jpg',
                                        legacy_location='LeadUpload/receipt/2021/7.jpg', legacy_checked_at=datetime.datetime.now(datetime.timezone.utc))
        r = m.Receipt.objects.create(origin='legacy_cash_receipt', number='C-0121210007', document=doc, received_as=1)
        self.client.force_login(User.objects.create_user('office', password='x', is_staff=True))
        self.assertTrue(self.client.get(f'/api/receipts/{r.pk}/').json()['document']['available'])
        self.assertEqual(self.client.get(f'/api/receipts/{r.pk}/document/').status_code, 302)
        from apps.valuations.test_forms import user_with_role
        self.client.force_login(user_with_role('157', m.Employee.objects.create(name='Assessor')))
        self.assertEqual(self.client.get(f'/api/receipts/{r.pk}/document/').status_code, 404)    # not their receipt
