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

Deciding the pending approval, sending a chat message and flipping a switch also push an event on `/admin/stream`, so the sidebar shows **Live** and panels refresh without waiting for the next poll.
A test keeps the mock in step with the API client: every path the client calls must have a mock route.

The real data contract is in `../docs/superpowers/plans/2026-10-03-foureyes-backend.md` (Task 14). When the gateway disagrees with `src/api/types.ts`, the types are what to fix.
