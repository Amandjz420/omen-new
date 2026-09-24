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
from django.http import FileResponse

from . import models as m
from .intake import IntakeError

MAX_BYTES = 25 * 1024 * 1024          # the legacy photo limit, 26,214,400 bytes
KINDS = {'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'bmp': 'image/bmp',
         'pdf': 'application/pdf', 'doc': 'application/msword',
         'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
ACCEPTS = {'photo': {'jpeg', 'png', 'webp', 'bmp'},
           'document': {'pdf', 'doc', 'docx', 'jpeg', 'png', 'webp'}}
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
                   'document': 'PDF, Word documents or images'}[purpose]
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


def serve(document):
    if document is None:
        raise IntakeError('File not found', 404)
    if document.storage_provider != 'local':
        raise IntakeError('This file is held in legacy storage and has not been retrieved yet', 404)
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / document.storage_key).resolve()
    if not path.is_relative_to(root) or not path.exists():
        raise IntakeError('The file is missing', 404)
    kind = path.suffix.lstrip('.')
    response = FileResponse(path.open('rb'), content_type=document.media_type or 'application/octet-stream',
                            filename=document.original_name or path.name, as_attachment=kind not in INLINE)
    # Never let a browser reinterpret an upload as something executable.
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
    return response


def file_json(document):
    if document is None:
        return None
    return {'id': document.pk, 'name': document.original_name, 'type': document.media_type,
            'size': document.size_bytes, 'local': document.storage_provider == 'local'}
