# FourEyes dashboard (UI)

React + TypeScript + Vite. No UI framework and no chart library; charts are plain SVG. Built into `../src/foureyes/ui_dist` and served by the gateway at `/ui/`.
Design: `../docs/superpowers/specs/2026-10-04-foureyes-ui-design.md`.

## Run it

```bash
npm install
npm run dev:mock     # the dashboard on http://127.0.0.1:5173/ui/ with a made-up gateway behind it
npm run dev          # the dashboard only, against a real gateway on 127.0.0.1:8080 (override with GATEWAY=http://host:port)
npm test             # unit and component tests
npm run typecheck
npm run build
```

## Build it and serve it from the gateway

From the repository root:

```bash
make ui     # npm install, type check and build into src/foureyes/ui_dist
make run    # the gateway serves the dashboard at http://127.0.0.1:8080/ui/
```

**The built bundle is committed** (`src/foureyes/ui_dist/`), so nobody needs Node to run the dashboard: `make run` is enough. After changing the UI, run `make ui` and commit the result together with the change. File names in the bundle are hashed, so every rebuild replaces files; to avoid conflicts, rebuild once as the last step before a release rather than in every PR. Fonts (Inter, JetBrains Mono, Latin and Latin Extended) are bundled; the dashboard needs no network.

## Smoke check against the real gateway

```bash
make run                              # one terminal
make smoke                            # another
POLICY_FILE=policy.yaml make smoke    # also changes the live policy and watches the dashboard data follow
```

`ui/scripts/smoke.mjs` (plain Node) checks, against a running gateway: the bundle and its fonts are served at `/ui/`; every endpoint the dashboard calls has the fields it reads; a clean prompt is answered locally; an injection is blocked with rule and OWASP tag; a poisoned client document is stopped and held (`ALLOW > BLOCK > APPROVAL`); the session shows `high_risk` with the approval waiting and a data flow; denying sticks and a second decision does not flip it; the audit export filters and gives CSV; the event stream pushes a decision. With `POLICY_FILE` it also removes a control from that file, waits for the gateway to reload, checks that posture drops, the control reads `REMOVED` and the policy version changes, then puts the file back. It exits 1 if anything fails. It sends a few messages through the gateway, so it leaves a few sessions behind; it denies the approval it creates.

## The mock gateway (`npm run mock`)

`mock/` is a stand-in for the gateway's admin API, with the shapes from the backend plan (Task 14). Plain Node, no dependencies, same port as the real gateway (`MOCK_PORT` changes it). All numbers are made up.
Use it to work on the UI without the backend, to demo, and to see the states that are hard to cause for real.

Controls page: **http://127.0.0.1:8080/__mock/** (also reachable through the dev server at `/__mock/`):

| Switch | What you see |
|---|---|
| A control was removed | posture drops, controls table row struck through, OWASP tile uncovered, new policy version, alert bar |
| Slow gateway | every answer takes 2.5 s: loading skeletons |
| Gateway down | every request fails with 503: errors with Retry, then the offline banner |
| Reset | back to the start, forgetting decisions and chats |

Deciding the pending approval, sending a Playground message and flipping a switch also push an event on `/admin/stream`, so the sidebar shows **Live** and panels refresh without waiting for the next poll.
A test keeps the mock in step with the API client: every path the client calls must have a mock route.

The real data contract is in `../docs/superpowers/plans/2026-10-03-foureyes-backend.md` (Task 14). When the gateway disagrees with `src/api/types.ts`, the types are what to fix.
