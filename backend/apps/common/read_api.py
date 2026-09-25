import json
from django.http import JsonResponse
from target_core.models import Lead, SourceIdentity, SourceRow


def page(request, qs, serialize):
    try:
        number = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        return JsonResponse({'error': 'page must be an integer'}, status=400)
    count = qs.count()
    rows=list(qs[(number - 1)*30:number*30])
    references=source_references(rows+[r.office for r in rows if isinstance(r,Lead) and r.office])  # offices resolve alongside their leads
    return JsonResponse({'count': count, 'page': number, 'page_size': 30,
                         'results': [serialize(r,references) for r in rows]})


def source_references(objects):
    """Map each target id to its legacy source id and the importer's issues for
    that row, so a corrected or cleared classification is visible rather than
    presented as if it were clean source data."""
    ids=[o.id for o in objects if o is not None]
    identities=list(SourceIdentity.objects.filter(environment='main',target_id__in=ids))
    by_table={}
    for r in identities:
        by_table.setdefault((r.schema,r.table),[]).append(r.key)
    problems={}
    for (schema,table),keys in by_table.items():
        for row in SourceRow.objects.filter(schema=schema,table=table,key__in=keys):
            problems[(schema,table,row.key)]=row.problems or []
    return {r.target_id:{'source_id':json.loads(r.key)[0][1],
                         'issues':problems.get((r.schema,r.table,r.key),[])} for r in identities}

