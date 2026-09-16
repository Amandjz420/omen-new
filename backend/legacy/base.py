from django.db import connections, models


def read_only(*args, **kwargs):
    raise PermissionError('Full-dump baseline is read-only. Port and validate business writes before enabling them.')


class ReadOnlyQuerySet(models.QuerySet):
    create = update = delete = bulk_create = bulk_update = get_or_create = update_or_create = read_only
    _raw_delete = read_only


class ReadOnlyModel(models.Model):
    objects = ReadOnlyQuerySet.as_manager()
    save = delete = read_only
    class Meta:
        abstract = True


class LegacyTable:
    """Bounded access for tables lacking a true key. No fabricated ORM identity."""
    def __init__(self, schema, table, columns):
        self.schema, self.table, self.columns = schema, table, tuple(columns)

    def count(self):
        with connections[self.schema].cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM `{self.table}`')
            return cursor.fetchone()[0]

    def rows(self, limit=100, offset=0, **filters):
        if not isinstance(limit, int) or not 1 <= limit <= 1000 or not isinstance(offset, int) or offset < 0:
            raise ValueError('limit must be 1–1000; offset must be nonnegative')
        if set(filters) - set(self.columns):
            raise ValueError('Unknown column')
        clauses, values = [], []
        for key, value in filters.items():
            clauses.append(f'`{key}` IS NULL' if value is None else f'`{key}` = %s')
            if value is not None:
                values.append(value)
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        sql = f'SELECT * FROM `{self.table}`{where} LIMIT %s OFFSET %s'
        with connections[self.schema].cursor() as cursor:
            cursor.execute(sql, values + [limit, offset])
            names = [c[0] for c in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]


class LegacyRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label.startswith('legacy_'):
            return model._meta.app_label.removeprefix('legacy_')

    def db_for_write(self, model, **hints):
        if model._meta.app_label.startswith('legacy_'):
            raise PermissionError('Legacy database writes are disabled')

    def allow_relation(self, obj1, obj2, **hints):
        labels = [obj1._meta.app_label, obj2._meta.app_label]
        if any(x.startswith('legacy_') for x in labels):
            return labels[0] == labels[1]

    def allow_migrate(self, db, app_label, **hints):
        if db != 'default' or app_label.startswith('legacy_'):
            return False

