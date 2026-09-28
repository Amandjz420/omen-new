"""Storing and serving files uploaded by users.

A file's kind is decided from its first bytes, never from its name or the type the
browser reports, since both are chosen by the uploader. Files are stored under a
generated name inside MEDIA_ROOT, so an uploaded name can never become a path.

What each purpose accepts follows the legacy data:
  * Photos were JPEG and PNG (58,711), plus 6 BMP. WebP is added for modern phones.
  * Documents attached to answers were labelled "PDF" by the legacy code whatever
    they were; in fact they were PDF, Word, images, 174 zip/rar archives and 9
    half-finished browser downloads. PDF, Word and images are accepted. Archives
    are refused: they cannot be previewed and are the usual carrier for malware.
"""
import io
import re
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import FileResponse

from target_core import models as m
from apps.common.http import IntakeError

MAX_BYTES = 25 * 1024 * 1024          # the legacy photo limit, 26,214,400 bytes
KINDS = {'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'bmp': 'image/bmp',
         'pdf': 'application/pdf', 'doc': 'application/msword',
         'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         # Site recordings: Android records WebM, iPhones MP4 audio.
         'webm': 'audio/webm', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4', 'wav': 'audio/wav', 'mp3': 'audio/mpeg'}
ACCEPTS = {'photo': {'jpeg', 'png', 'webp', 'bmp'},
           'document': {'pdf', 'doc', 'docx', 'jpeg', 'png', 'webp'},
           'recording': {'webm', 'ogg', 'm4a', 'wav', 'mp3'},
           'page': {'jpeg', 'png', 'webp'}}
# MP4 is also the container for iPhone HEIC photos and for video; only these brands are audio here.
AUDIO_BRANDS = {b'M4A ', b'M4B ', b'mp41', b'mp42', b'isom', b'iso2', b'iso5', b'iso6', b'dash'}
INLINE = {'jpeg', 'png', 'webp', 'bmp', 'pdf'}


def sniff(content):
    """The file's real kind, from its signature, or None."""
    if content[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if content[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'webp'
    if content[:2] == b'BM':
        return 'bmp'
    if content[:5] == b'%PDF-':
        return 'pdf'
    if content[:4] == b'\x1a\x45\xdf\xa3':
        return 'webm'
    if content[:4] == b'OggS':
        return 'ogg'
    if content[4:8] == b'ftyp' and content[8:12] in AUDIO_BRANDS:
        return 'm4a'
    if content[:4] == b'RIFF' and content[8:12] == b'WAVE':
        return 'wav'
    if content[:3] == b'ID3' or content[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        return 'mp3'
    if content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return 'doc'
    if content[:4] == b'PK\x03\x04':
        # Word documents are zip containers; a plain archive is not a Word file.
        try:
            names = zipfile.ZipFile(io.BytesIO(content)).namelist()
        except zipfile.BadZipFile:
            return None
        return 'docx' if 'word/document.xml' in names else None
    return None


def clean_name(name):
    base = re.split(r'[\\/]', name or '')[-1]
    return re.sub(r'[\x00-\x1f]', '', base).strip()[:250] or 'upload'


def read(upload, purpose):
    """Validate an upload and return (content, kind). Raises IntakeError."""
    if upload is None:
        raise IntakeError('Choose a file to upload')
    if upload.size > MAX_BYTES:
        raise IntakeError(f'The file is larger than {MAX_BYTES // (1024 * 1024)} MB')
    content = upload.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise IntakeError(f'The file is larger than {MAX_BYTES // (1024 * 1024)} MB')
    kind = sniff(content)
    if kind not in ACCEPTS[purpose]:
        allowed = {'photo': 'JPEG, PNG, WebP or BMP images',
                   'document': 'PDF, Word documents or images',
                   'recording': 'a WebM, MP4, Ogg, WAV or MP3 recording',
                   'page': 'photographs of the pages (JPEG, PNG or WebP)'}[purpose]
        raise IntakeError(f'This file type is not accepted. Upload {allowed}.')
    return content, kind


def store(upload, purpose, folder):
    """Validate, record and write an upload; returns its Document. The file is
    written after the record is created, inside the caller's transaction, so a
    failure to write rolls the record back."""
    content, kind = read(upload, purpose)
    relative = f'{folder}/{uuid.uuid4().hex}.{kind}'
    document = m.Document.objects.create(storage_provider='local', storage_key=relative,
                                         original_name=clean_name(upload.name), media_type=KINDS[kind],
                                         size_bytes=len(content))
    path = Path(settings.MEDIA_ROOT) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return document


# Where the previous system's files live, verified against the bucket and the
# local folder by manage.py locate_legacy_files, which records each document's
# exact location:
#   * Lead documents: the S3 bucket, under LeadUpload/ plus the stored key. The
#     bucket holds both forms of a doubled slash: 143,973 keys exist as stored,
#     including some with "//", and 6,663 only with it collapsed. Neither rule alone
#     works, so the location is recorded, not guessed.
#   * User-management uploads: the local copy of its upload folder, else the
#     bucket's UAMUpload/ folder, which holds only 80 older files.
PREFIX = {'legacy_lead_s3': 'LeadUpload/', 'legacy_uam_local': 'UAMUpload/'}
LOCAL_MARK = 'local:'


def s3_key(document):
    """The object key to request: the verified location, or before files have been
    located, the stored key as it is, which is right for most."""
    if document.storage_provider not in PREFIX:
        return None
    if document.legacy_location and not document.legacy_location.startswith(LOCAL_MARK):
        return document.legacy_location
    if document.legacy_checked_at:
        return None                                      # located, and not in the bucket
    return PREFIX[document.storage_provider] + document.storage_key.lstrip('/')


def contained(root, key):
    root = Path(root).resolve()
    path = (root / key).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def local_path(document):
    if document.storage_provider == 'local':
        return contained(settings.MEDIA_ROOT, document.storage_key)
    if document.storage_provider == 'legacy_uam_local':
        return contained(settings.LEGACY_UAM_ROOT, document.storage_key)
    return None


def available(document):
    """Whether this server can hand the file over: stored here, in the local copy of
    the previous system's uploads, or in the bucket with its credentials configured.
    Once located, a file found in neither place is not available."""
    from . import s3
    if document is None:
        return False
    if document.storage_provider == 'local':
        return True
    if document.storage_provider == 'legacy_uam_local' and local_path(document) is not None:
        return True
    return s3_key(document) is not None and s3.configured()


def kind_of(document, name):
    return (Path(name).suffix.lstrip('.') or (document.media_type or '').split('/')[-1]).lower()


def media_type(document, name):
    import mimetypes
    # Imported types are sometimes incomplete ("image"), which browsers reject.
    stored = document.media_type if '/' in (document.media_type or '') else ''
    return stored or mimetypes.guess_type(name)[0] or 'application/octet-stream'


def serve(document):
    from . import s3
    if document is None:
        raise IntakeError('File not found', 404)
    path = local_path(document)
    if path is None and document.storage_provider != 'local' and s3_key(document):
        # A file from the previous system's bucket. Access was checked by the caller;
        # the browser is sent a link valid for five minutes, and the credentials stay
        # here. The file is served from Amazon's domain, not this one, so a hostile
        # legacy upload cannot run script against the application.
        if not s3.configured():
            raise IntakeError("Files from the previous system are not connected on this server", 503)
        name = document.original_name or Path(document.storage_key).name
        url = s3.presign(s3_key(document), filename=name, content_type=media_type(document, name),
                         attachment=kind_of(document, name) not in INLINE)
        response = HttpResponseRedirect(url)
        response['Cache-Control'] = 'no-store'
        return response
    if path is None:
        raise IntakeError('The file is missing', 404)
    kind = path.suffix.lstrip('.').lower()
    response = FileResponse(path.open('rb'), content_type=media_type(document, path.name),
                            filename=document.original_name or path.name, as_attachment=kind not in INLINE)
    # Never let a browser reinterpret an upload as something executable.
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
    return response


def read_bytes(document, limit=20 * 1024 * 1024):
    """A file's content, for embedding in a generated PDF; None if it cannot be had."""
    from . import s3
    import urllib.request
    if document is None:
        return None
    path = local_path(document)
    if path is not None:
        return path.read_bytes() if path.stat().st_size <= limit else None
    if s3_key(document) and s3.configured():
        try:
            with urllib.request.urlopen(s3.presign(s3_key(document)), timeout=20) as r:
                data = r.read(limit + 1)
            return data if len(data) <= limit else None
        except Exception:
            return None
    return None


def file_json(document):
    if document is None:
        return None
    # 'available': this server can hand the file over. 'local': it was stored here.
    return {'id': document.pk, 'name': document.original_name, 'type': document.media_type,
            'size': document.size_bytes, 'local': document.storage_provider == 'local',
            'available': available(document)}
