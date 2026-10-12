"""Signed, short-lived download links for the legacy S3 bucket.

AWS Signature Version 4 query-string signing ("presigned URLs"), written with the
standard library so no SDK is needed. The credentials come from the environment
(the repository's .env, loaded by config.settings) and never reach the browser:
the server checks access first, then hands the browser a link valid for a few
minutes.

Tested against the worked example in the AWS documentation (Authenticating
Requests: Using Query Parameters), whose signature is published.
"""
import datetime
import hashlib
import hmac
import os
from urllib.parse import quote

EXPIRES = 300                      # seconds a link stays valid


def upload(key, content, content_type):
    """Private object upload using the existing bucket; never sets a public ACL."""
    from urllib.request import Request, urlopen
    from apps.common.http import IntakeError
    if not configured():
        raise IntakeError('S3 storage is not configured on this server.', 503)
    try:
        request = Request(presign(key, method='PUT'), data=content, method='PUT',
                          headers={'Content-Type': content_type})
        with urlopen(request, timeout=90) as response:
            if response.status not in (200, 201):
                raise OSError('Upload failed')
    except (OSError, TimeoutError):
        raise IntakeError('The recording could not be saved to S3. Keep the recording and retry the upload.', 503) from None


def configured():
    return all(os.environ.get(k) for k in ('AWS_S3_BUCKET_NAME', 'AWS_DEFAULT_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'))


def _sign(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def presign(key, *, bucket=None, region=None, access_key=None, secret_key=None, expires=EXPIRES, now=None,
            filename=None, host=None, method='GET', query=None, content_type=None, attachment=False):
    bucket = bucket or os.environ['AWS_S3_BUCKET_NAME']
    region = region or os.environ['AWS_DEFAULT_REGION']
    access_key = access_key or os.environ['AWS_ACCESS_KEY_ID']
    secret_key = secret_key or os.environ['AWS_SECRET_ACCESS_KEY']
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp, day = now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%Y%m%d')
    host = host or (f'{bucket}.s3.amazonaws.com' if region == 'us-east-1' else f'{bucket}.s3.{region}.amazonaws.com')
    path = '/' + quote(key.lstrip('/'), safe='/-_.~')
    scope = f'{day}/{region}/s3/aws4_request'
    params = {'X-Amz-Algorithm': 'AWS4-HMAC-SHA256', 'X-Amz-Credential': f'{access_key}/{scope}', 'X-Amz-Date': stamp,
              'X-Amz-Expires': str(expires), 'X-Amz-SignedHeaders': 'host'}
    if filename:
        safe = ''.join(c if 32 <= ord(c) < 127 and c not in '"\\' else '_' for c in filename)
        params['response-content-disposition'] = f'{"attachment" if attachment else "inline"}; filename="{safe}"'
    if content_type:
        params['response-content-type'] = content_type          # the bucket labels every file octet-stream
    params.update(query or {})
    token = os.environ.get('AWS_SESSION_TOKEN', '').strip('"').strip("'")
    if token:
        params['X-Amz-Security-Token'] = token                 # temporary credentials sign with their session token
    query = '&'.join(f'{quote(k, safe="-_.~")}={quote(v, safe="-_.~")}' for k, v in sorted(params.items()))
    canonical = '\n'.join([method, path, query, f'host:{host}\n', 'host', 'UNSIGNED-PAYLOAD'])
    to_sign = '\n'.join(['AWS4-HMAC-SHA256', stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = _sign(_sign(_sign(_sign(('AWS4' + secret_key).encode(), day), region), 's3'), 'aws4_request')
    signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return f'https://{host}{path}?{query}&X-Amz-Signature={signature}'
