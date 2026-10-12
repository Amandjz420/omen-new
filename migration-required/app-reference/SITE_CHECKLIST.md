# Site completion checklist

Implemented 29 September 2026. No database migration is required.

## Using it

Open a valuation in the full form or the phone form and select **Before leaving the site**.

- Required information lists unanswered required questions across the valuation, with their sections.
- **Ask a focused follow-up** asks about the first outstanding question. **Help me answer** asks about a particular one.
- AI rewrites the original question briefly. It receives the question, answer type and option labels, not the valuation's documents, recordings or customer details.
- The original question remains visible for comparison. **Answer this question** opens its section; the phone form also scrolls to the question.
- Answers are entered through the existing form controls. Voice answers still use the existing recording → suggestions → acceptance process.
- Photographs and plans lists the six expected categories, with upload buttons for missing or unavailable files.
- Unsaved device drafts and unsaved full-form edits trigger a warning. Only server-saved answers count as complete.

## Rules and limitations

Required-question detection reuses `submission.unanswered_required`, including its service/subtype scope and active/mandatory/deleted rules. Whitespace-only answers do not satisfy a question. A saved numeric zero does.

The checklist covers all required questions, including office/post-site questions. It does not infer new mandatory requirements or claim that every optional inspection field has been completed.

Expected photo categories come from `files.EXPECTED`: Front, Inside, Right View, Left View, Location Plan, Site Plan. These are the existing general expectations, not mandatory rules for every asset or bank. They do not block submission. There is no per-case “not applicable” override in this version.

Local file existence is checked. Remote availability uses the existing document metadata and storage configuration; opening the checklist does not download or inspect S3 objects. “File recorded” does not certify the image's subject, quality or current remote existence.

AI cannot mark a requirement complete, write an answer, or approve a valuation. Missing/failed AI configuration falls back to the original question. AI wording is limited to 240 characters and is advisory; semantic accuracy still needs review. A question answered while the AI request is running is rejected as stale.

## API and code

- `GET /api/valuations/<uuid>/checklist/`: missing required questions, expected photo statuses, remaining counts, editability and AI configuration status.
- `POST /api/valuations/<uuid>/checklist/follow-up/`: accepts `{}` for the first outstanding question, or `{"question": "<uuid>"}` for one specific unanswered required question. Returns a prompt with original text, question ID, section key and `ai_generated` flag. Returns 409 for stale/non-required questions or non-editable valuations.
- Both endpoints enforce the existing staff and case access rules. Photo uploads use the existing photo endpoint and its validation/auditing.
- Backend: `backend/apps/valuations/checklist.py`.
- Shared UI: `frontend/src/screens/SiteChecklist.jsx`.
- Form integrations: `frontend/src/screens/ValuationForm.jsx` and `frontend/src/valuations.jsx`.

## Verification

Backend checklist and submission tests: 22 passed. Frontend checklist and phone-form tests: 15 passed. Production frontend build passed.

Tests cover blank/retired/optional questions, saved zero, photo upload and missing local files, AI fallback, no answer writes from prompts, stale questions, assessor access restrictions, closed valuations, question navigation, device drafts, and offline checklist errors.

Live browser verification confirmed checklist counts on an existing valuation, a DeepInfra-generated follow-up, navigation to its original question, and the 390-pixel phone layout. No business answers or photos were changed during this browser check. The existing recording/S3 upload problem was not re-tested as part of this feature.
