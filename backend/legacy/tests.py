import importlib
from django.test import SimpleTestCase
from legacy.base import LegacyRouter, LegacyTable
from legacy.catalog import catalog, table


class FullDatabaseMappingTests(SimpleTestCase):
    def test_complete_table_coverage(self):
        specs = catalog()
        self.assertEqual(len(specs), 982)
        self.assertEqual(sum(s['access'] == 'orm' for s in specs.values()), 905)
        self.assertEqual(sum(s['access'] == 'keyless_reader' for s in specs.values()), 77)
        self.assertEqual(sum(len(s['primary_key']) > 1 for s in specs.values()), 106)
        for (schema, name), spec in specs.items():
            entity = table(schema, name)
            if spec['access'] == 'orm':
                self.assertFalse(entity._meta.managed)
                self.assertEqual(entity._meta.db_table, name)
                self.assertEqual({f.column for f in entity._meta.local_fields if f.column}, set(spec['fields']))
            else:
                self.assertIsInstance(entity, LegacyTable)
                self.assertEqual(set(entity.columns), set(spec['fields']))

    def test_reads_route_to_original_schema(self):
        router = LegacyRouter()
        main = table('lead_mngt', 'lead')
        uat = table('lead_mngt_uat', 'lead')
        self.assertEqual(router.db_for_read(main), 'lead_mngt')
        self.assertEqual(router.db_for_read(uat), 'lead_mngt_uat')
        self.assertFalse(router.allow_relation(main(), uat()))
        self.assertFalse(router.allow_migrate('lead_mngt', 'core'))
        self.assertFalse(router.allow_migrate('default', 'legacy_lead_mngt'))

    def test_no_implicit_model_or_bulk_writes(self):
        lead = table('lead_mngt', 'lead')
        for operation in [lambda: lead().save(), lambda: lead().delete(),
                          lambda: lead.objects.all().update(lead_status=1), lambda: lead.objects.all().delete(),
                          lambda: lead.objects.bulk_create([]), lambda: LegacyRouter().db_for_write(lead)]:
            with self.assertRaises(PermissionError):
                operation()

    def test_keyless_identifiers_are_allowlisted(self):
        bank = table('uam_user', 'bank')
        with self.assertRaises(ValueError):
            bank.rows(**{'unknown`': 'x'})
        with self.assertRaises(ValueError):
            bank.rows(limit=1001)
        with self.assertRaises(ValueError):
            table('uam_user', 'bank; DROP TABLE bank')
