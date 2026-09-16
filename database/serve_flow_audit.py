"""Disposable loopback-only browser test server. Never opens target.sqlite3.

Run with backend/.venv/bin/python database/serve_flow_audit.py after building React.
All fixture data and credentials exist only in a temporary SQLite database.
"""
import os
from pathlib import Path
import secrets
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DJANGO_DEBUG'] = '1'
os.environ['DJANGO_SECRET_KEY'] = secrets.token_urlsafe(40)


def main():
    from django.conf import settings
    with tempfile.TemporaryDirectory(prefix='omen-flow-audit-') as folder:
        settings.DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3', 'NAME':str(Path(folder)/'audit.sqlite3')}}
        settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
        settings.SESSION_COOKIE_NAME = 'omen_flow_audit_session'
        settings.CSRF_COOKIE_NAME = 'omen_flow_audit_csrf'
        import django
        django.setup()
        from django.core.management import call_command
        from django.contrib.auth import get_user_model
        from django.core.wsgi import get_wsgi_application
        from django.db import connections
        from django.urls import path
        from django.views.static import serve
        from config import urls
        from target_core.test_flow_contracts import seed_flow_example
        from wsgiref.simple_server import make_server
        call_command('migrate', verbosity=0)
        seed_flow_example()
        password = secrets.token_urlsafe(20)
        get_user_model().objects.create_user('flow-audit', password=password, is_staff=True)
        def frontend(request, resource=''):
            return serve(request, resource or 'index.html', document_root=str(ROOT/'frontend/dist'))
        urls.urlpatterns += [path('', frontend), path('<path:resource>', frontend)]
        with make_server('127.0.0.1', 8187, get_wsgi_application()) as server:
            print('Synthetic-only browser audit: http://127.0.0.1:8187/', flush=True)
            print('Temporary username: flow-audit; password: '+password, flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
        connections.close_all()


if __name__ == '__main__':
    main()
