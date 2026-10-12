"""The DeepInfra models behind answer suggestions.

Speech is transcribed by Whisper Large V3 through DeepInfra's inference endpoint; pages
are read, and sources matched to the form's questions, by Qwen3-VL through its
OpenAI-compatible chat endpoint. Both are zero-retention on DeepInfra. The key is
read from the environment (DEEPINFRA_API_KEY, in the repository's git-ignored
.env), sent only in the Authorization header, and never put into an error.
"""
import base64
import json
import os
import re
import urllib.error
import urllib.request
import uuid

BASE = 'https://api.deepinfra.com'
TIMEOUT = 180


class AssistError(Exception):
    """A failure the person can understand; never carries the key or a raw response."""


def _clean(value):
    return (value or '').strip().strip('"').strip("'")


def configured():
    return bool(_clean(os.environ.get('DEEPINFRA_API_KEY')))


def models():
    return {'transcribe': _clean(os.environ.get('OMEN_ASR_MODEL')) or 'openai/whisper-large-v3',
            'read': _clean(os.environ.get('OMEN_VISION_MODEL')) or 'Qwen/Qwen3-VL-235B-A22B-Instruct'}


def _key():
    key = _clean(os.environ.get('DEEPINFRA_API_KEY'))
    if not key:
        raise AssistError('Answer suggestions are not set up on this server: DEEPINFRA_API_KEY is empty.')
    return key


def _send(request, what):
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        reason = {401: 'the DeepInfra key was refused', 402: 'the DeepInfra account needs credit',
                  413: 'the file is too large for the service',
                  429: 'the service is busy; try again shortly'}.get(exc.code, f'it answered {exc.code}')
        raise AssistError(f'The {what} service could not be used: {reason}.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AssistError(f'The {what} service did not answer. Check the connection and try again.') from None
    except ValueError:
        raise AssistError(f'The {what} service sent a reply that could not be read.') from None


def transcribe(audio, filename, media_type):
    """Speech to text: {'text', 'segments': [{'start', 'end', 'text'}], 'language', 'duration'}."""
    boundary = uuid.uuid4().hex
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', filename or 'recording')
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="{safe}"\r\n'
            f'Content-Type: {media_type}\r\n\r\n').encode() + audio + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(f"{BASE}/v1/inference/{models()['transcribe']}", data=body, method='POST', headers={
        'Authorization': f'Bearer {_key()}', 'Content-Type': f'multipart/form-data; boundary={boundary}'})
    data = _send(request, 'speech')
    segments = [{'start': float(s.get('start') or 0), 'end': float(s.get('end') or 0), 'text': (s.get('text') or '').strip()}
                for s in data.get('segments') or [] if (s.get('text') or '').strip()]
    # The text field can be empty while the segments carry the words, as in DeepInfra's own example.
    text = (data.get('text') or '').strip() or ' '.join(s['text'] for s in segments)
    return {'text': text, 'segments': segments, 'language': data.get('language') or '',
            'duration': data.get('duration') or (segments[-1]['end'] if segments else None)}


def chat(messages, max_tokens=4000, json_reply=False):
    body = {'model': models()['read'], 'messages': messages, 'temperature': 0, 'max_tokens': max_tokens}
    if json_reply:
        body['response_format'] = {'type': 'json_object'}
    request = urllib.request.Request(f'{BASE}/v1/openai/chat/completions', data=json.dumps(body).encode(), method='POST',
                                     headers={'Authorization': f'Bearer {_key()}', 'Content-Type': 'application/json'})
    data = _send(request, 'reading')
    try:
        return data['choices'][0]['message']['content'] or ''
    except (KeyError, IndexError, TypeError):
        raise AssistError('The reading service sent a reply that could not be read.') from None


def read_page(image, media_type):
    """One photographed page, transcribed as printed: lines kept, Hindi in Devanagari."""
    url = f'data:{media_type};base64,{base64.b64encode(image).decode()}'
    return chat([
        {'role': 'system', 'content': 'You transcribe photographed pages of Indian property documents such as sale deeds. '
         'Write out all the text exactly as printed or handwritten, line by line, in its own language and script '
         '(Hindi in Devanagari, English as written). Keep numbers, names and punctuation exactly. Do not translate, '
         'summarise, explain or add anything. If a part is unreadable, write [unreadable].'},
        {'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': url}},
                                     {'type': 'text', 'text': 'Transcribe this page.'}]}], max_tokens=6000).strip()


def answer_json(system, user):
    """The matching step: a JSON object, parsed even when wrapped in a code fence."""
    reply = chat([{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], max_tokens=6000, json_reply=True)
    text = re.sub(r'^\s*```(?:json)?|```\s*$', '', reply.strip())
    try:
        return json.loads(text)
    except ValueError:
        match = re.search(r'\{.*\}', text, re.S)
        try:
            return json.loads(match.group(0)) if match else {}
        except ValueError:
            raise AssistError('The reading service sent answers that could not be read.') from None
