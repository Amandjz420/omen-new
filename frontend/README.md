# Omen Assessors workspace — frontend

React 19 with Mantine 9, React Router 8 and TanStack Query 5, built with Vite.

## Running it

    npm run dev          # http://127.0.0.1:5173, with /api proxied to Django on :8000
    npm test             # unit and component tests (Vitest)
    npm run e2e          # browser tests on a desktop and an Android phone (Playwright)
    npm run build

Each script sets its own `NODE_ENV`. This machine's shell exports
`NODE_ENV=production`, which made npm skip development packages and loaded React's
production build into tests; install with `npm install --include=dev`, or remove
the setting from your shell profile.

The browser tests always check the sign-in screen and, with the backend replaced by
sample responses, the signed-in layout; they save screenshots to
`test-results/shots/`. The journey against the real backend runs when a login is
supplied in the environment, never in the code:

    E2E_USERNAME=... E2E_PASSWORD=... npm run e2e

## Layout of the code

| Path | What it is |
| --- | --- |
| `src/main.jsx` | Providers and every route. Workflow screens load when first opened. |
| `src/app/` | The theme, the session gate, navigation (`nav.js`), and the shell. |
| `src/lib/` | `api.js` (the only way to call the backend), `format.js`, `drafts.js`, `uuid.js`. |
| `src/components/` | Shared building blocks: `PageHeader`, `Money`, `StatusBadge`, `StageTrack`, loading, empty and error states, `confirmAction`. |
| `src/screens/` | Screens built on the new foundations. |
| `src/*.jsx` | Screens from the previous interface, hosted unchanged by `LegacyScreen` until each is rebuilt. Their styles are confined to `.legacy-screen` in `legacy.css`. |
| `e2e/` | Playwright tests. |

## Conventions

- **Brand.** Omen blue `#357ABF`, from the previous site's header, is the primary
  colour; ink `#16324F` is text. The wordmark is the only place for spaced capitals.
- **Phones first for assessors.** Touch targets of at least 44 px, no sideways
  scrolling, and a bottom bar on phones. A closed phone menu is `inert`.
- **Retry-safe actions** take an operation ID from `uuid()` in `lib/uuid.js`, which
  also works over plain http on the office network, where `crypto.randomUUID` does not.
  Keep the ID when a request fails; make a new one after success.
- **Forms send an explicit list of fields**, declared once and compared with the
  backend by a test (see `WRITE_FIELDS` in `receipts.jsx`), never a spread of a
  previous response.
- **Ask before irreversible actions** with `confirmAction`, stating the consequence.
- **Drafts** entered at a site are written with `saveDraft` first, so a dropped
  connection never loses work.
- **Amounts** use `Money` or `rupees()`: Indian grouping, fixed-width figures.

## Rebuilding a carried-over screen

Replace its `legacy(...)` route in `main.jsx` with a screen in `src/screens/`, built
from the shared components, with a route of its own for each record so it can be
bookmarked, and tests for its requests. Remove its rules from `legacy.css` once no
carried-over screen uses them.
