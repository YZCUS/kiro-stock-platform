# Frontend routing and auth stability

This note documents the frontend guard pattern used to prevent blank pages,
infinite loading states, and hydration mismatches in the Next.js App Router UI.

## Auth initialization

Auth state is restored on the client by `AuthInit`.

- `auth.initialized = false` means localStorage has not been checked yet.
- `auth.initialized = true` means the app can safely decide whether the user is
  authenticated.
- `restoreAuth` and `loginSuccess` both set `initialized = true`.
- If no valid localStorage session exists, `AuthInit` dispatches
  `authInitialized()`.

Protected pages must wait for `initialized` before redirecting. Do not redirect
based only on `isAuthenticated === false` during the first client render.

## Protected route pattern

`/stocks` is protected and should render in this order:

1. Server and first client render: stable placeholder.
2. After mount and auth initialization:
   - authenticated: render `StockManagementPage`.
   - unauthenticated: `router.replace('/login?redirect=/stocks')`.

The route also uses a mounted gate so the server-rendered placeholder matches
the first client render. This avoids dev-mode hydration errors when localStorage
restores a session immediately after hydration starts.

## Public route pattern

`/dashboard` is public. It should not redirect unauthenticated users. Logged-in
users get watchlist and portfolio controls; anonymous users still get the direct
symbol lookup and the page shell.

For public pages that optionally use auth, keep the base page renderable without
auth and guard only the authenticated data fetches.

## Next dev cache failure mode

During local development, Next.js can serve stale or missing route chunks after
large edits or after running `npm run build` while `next dev` is still running.
The browser symptom is usually one of:

- route chunk returns `404`, for example
  `/_next/static/chunks/app/dashboard/page.js`.
- browser refuses to execute a JS chunk because it received HTML.
- only the navigation renders, or the page stays on a loading spinner.

Recovery:

```bash
pkill -f "next dev"
rm -rf frontend/.next
cd frontend
npm run dev
```

Avoid running `npm run build` while the dev server is serving pages.

## Verification checklist

For auth and routing changes, verify these paths with a fresh browser context:

- unauthenticated `/stocks` redirects to `/login?redirect=/stocks`.
- authenticated `/stocks` renders the stock management page.
- authenticated `/dashboard` renders the real-time analysis page.
- no `pageerror`, hydration mismatch, or route chunk `404` appears in headless
  browser logs.

Recommended local checks:

```bash
cd frontend
npm run lint
npm run build
```

Then restart a clean dev server and run a headless smoke test against
`/stocks` and `/dashboard`.
