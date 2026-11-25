"""The organisations-and-clients tree (client review 2026-11-25)."""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from target_core import models as m


class DirectoryTreeTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('directory', password='Only-for-tests-984!', is_staff=True)
        self.client.force_login(user)
        fi = m.ClientType.objects.get_or_create(name='Financial Institution')[0]
        corporate = m.ClientType.objects.get_or_create(name='Corporate')[0]
        self.sbi = m.Bank.objects.create(name='State Bank of India')
        canara = m.Bank.objects.create(name='Canara Bank')
        m.BankBranch.objects.create(name='MP NAGAR', bank=canara, ifsc='CNRB0001234')
        office = lambda **kw: m.ClientOffice.objects.create(client_type=kw.pop('client_type', fi), **kw)
        self.linked = office(name='State Bank of India', branch_name='Hoshangabad', bank=self.sbi, ifsc='SBIN0000383',
                             state='Madhya Pradesh', district='Hoshangabad')
        self.spelled = office(name='State Bank Of India', branch_name='Itarsi', state='Madhya Pradesh', district='Hoshangabad')
        self.by_prefix = office(name='SBI', branch_name='Pipariya', ifsc='SBIN0001111', state='Madhya Pradesh', district='Hoshangabad')
        self.by_directory = office(name='Canara', branch_name='MP Nagar', ifsc='CNRB0001234', state='Madhya Pradesh', district='Bhopal')
        self.unknown = office(name='Some cooperative', branch_name='Main', state='Madhya Pradesh', district='Bhopal')
        self.acme = office(name='Acme Ltd', client_type=corporate, state='Madhya Pradesh', district='Bhopal')
        self.poonam = m.Contact.objects.create(name='Poonam Salve', office=self.linked, phone='9826012345')
        m.Contact.objects.create(name='Ravi', office=self.linked, phone='9826000000')
        today = datetime.date.today()
        for office_, contact, days in ((self.linked, self.poonam, 400), (self.linked, self.poonam, 10), (self.acme, None, 5),
                                       (self.by_directory, None, 100)):
            m.Lead.objects.create(office=office_, contact=contact, received_date=today - datetime.timedelta(days=days))

    def get(self, path, **query):
        r = self.client.get(f'/api/directory/{path}/', query)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_branches_group_under_their_bank_however_they_are_linked(self):
        groups = {g['key']: g for g in self.get('groups')['groups']}
        sbi = groups[f'bank:{self.sbi.pk}']
        self.assertEqual((sbi['name'], sbi['branches'], sbi['clients'], sbi['leads']), ('State Bank of India', 3, 2, 2))
        self.assertEqual(groups[f'bank:{self.by_directory.pk and m.Bank.objects.get(name="Canara Bank").pk}']['branches'], 1)
        self.assertEqual((groups['none']['name'], groups['none']['branches']), ('Bank not identified', 1))
        self.assertEqual(groups['type:Corporate']['branches'], 1)

    def test_the_most_recent_work_comes_first(self):
        names = [g['name'] for g in self.get('groups')['groups']]
        self.assertEqual(names[:3], ['Corporate', 'State Bank of India', 'Canara Bank'])
        self.assertEqual(names[-1], 'Bank not identified')                       # no lead: last
        rows = self.get('branches', group=f'bank:{self.sbi.pk}')['results']
        self.assertEqual([r['branch'] for r in rows][0], 'Hoshangabad')
        by_name = self.get('branches', group=f'bank:{self.sbi.pk}', sort='name')['results']
        self.assertEqual([r['branch'] for r in by_name], ['Pipariya', 'Hoshangabad', 'Itarsi'])   # SBI, then State Bank...

    def test_filters(self):
        self.assertEqual([g['name'] for g in self.get('groups', type='Corporate')['groups']], ['Corporate'])
        self.assertEqual({g['name'] for g in self.get('groups', district='bhopal')['groups']},
                         {'Canara Bank', 'Bank not identified', 'Corporate'})
        active = self.get('groups', active='3')['groups']
        self.assertEqual({g['name'] for g in active}, {'Corporate', 'State Bank of India'})
        self.assertEqual([g['name'] for g in self.get('groups', bank=f'bank:{self.sbi.pk}')['groups']], ['State Bank of India'])
        filters = self.get('groups')['filters']
        self.assertIn({'name': 'Madhya Pradesh', 'districts': ['Bhopal', 'Hoshangabad']}, filters['states'])
        self.assertIn('Corporate', filters['types'])

    def test_a_branch_lists_its_clients_and_search_finds_both(self):
        clients = self.get('clients', office=str(self.linked.pk))['results']
        self.assertEqual([(c['name'], c['leads']) for c in clients], [('Poonam Salve', 2), ('Ravi', 0)])
        found = self.get('search', q='itarsi')
        self.assertEqual([b['branch'] for b in found['branches']], ['Itarsi'])
        found = self.get('search', q='98260 12345')
        self.assertEqual([c['name'] for c in found['clients']], ['Poonam Salve'])
        self.assertEqual(self.client.get('/api/directory/clients/', {'office': 'x'}).status_code, 400)
