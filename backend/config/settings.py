import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('Set DJANGO_SECRET_KEY for deployment')
    secret_file = BASE_DIR / '.local-secret'
    if not secret_file.exists():
        fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_urlsafe(48))
    SECRET_KEY = secret_file.read_text().strip()
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.messages', 'django.contrib.sessions', 'django.contrib.staticfiles',
                  'target_core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware',
              # Onboarding is enforced for the admin site too, not just the API.
              'target_core.middleware.RequirePasswordChange',
              'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'DIRS': [],
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Documents this system generates, such as work orders. Local until object
# storage is configured; gitignored, never served statically.
MEDIA_ROOT = Path(os.environ.get('OMEN_MEDIA_ROOT', BASE_DIR.parent / 'storage'))
WSGI_APPLICATION = 'config.wsgi.application'
# PostgreSQL is the application database. Credentials come from the environment
# in deployment, or from database/.local/postgres.json locally (gitignored, mode
# 600). DATABASE_ENGINE=sqlite selects the retired SQLite file, kept only for
# rollback and for the one-time transfer.
SQLITE_PATH = BASE_DIR / 'target.sqlite3'
POSTGRES_CONFIG = BASE_DIR.parent / 'database' / '.local' / 'postgres.json'


def _postgres():
    if os.environ.get('DATABASE_ENGINE', '').lower() == 'sqlite':
        return None
    if os.environ.get('POSTGRES_PASSWORD'):
        return {'host': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
                'port': int(os.environ.get('POSTGRES_PORT', '5433')),
                'name': os.environ.get('POSTGRES_DB', 'omen'),
                'user': os.environ.get('POSTGRES_USER', 'omen'),
                'password': os.environ['POSTGRES_PASSWORD']}
    if POSTGRES_CONFIG.exists():
        import json
        return json.loads(POSTGRES_CONFIG.read_text())
    if not DEBUG:
        raise RuntimeError('Set POSTGRES_* environment variables for deployment')
    return None


_pg = _postgres()
if _pg:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _pg['name'], 'USER': _pg['user'], 'PASSWORD': _pg['password'],
        'HOST': _pg['host'], 'PORT': str(_pg['port']),
        # Persistent connections; the importer holds one for long batches.
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'connect_timeout': 10},
    }}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': SQLITE_PATH}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'Asia/Kolkata'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:5173', 'http://localhost:5173'] if DEBUG else []
SECURE_CONTENT_TYPE_NOSNIFF = True
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
