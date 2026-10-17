# AutoQA dashboard — local development slice

React + TypeScript implements the Blueprint v2 primary journey: describe a test, preview original and interpreted steps, confirm the literal expectation with a different approver account, then run an approved snapshot. No credentials are shipped. Session cookies stay HTTP-only; the CSRF token is held only in React memory. The API remains responsible for enforcing authorization and immutable approval, regardless of disabled UI controls.

Use `npm ci --ignore-scripts` and `npm run build`. The backend serves `dist/` on its same origin. `npm run dev` is only a frontend development server; no API proxy or credentials are configured. This is an explicitly labelled synthetic local proof of concept, not an enterprise deployment.

## Dependencies

Direct versions are pinned in package.json and transitive resolution in package-lock.json. React 19.3.1 and react-dom 19.3.1 (MIT) supply the required interactive dashboard. TypeScript 7.0.2 (Apache-2.0) performs strict static checks. Vite 8.3.4 (MIT) builds local assets; @types/react and @types/react-dom 19.3.0 (MIT) provide compile-time typings. Licences were inspected in installed package licence files or package metadata. No externally loaded fonts, scripts, telemetry, or model calls are used. The Vite distribution also carries notices for bundled dependencies; retain those during redistribution.

## Verification performed on 2026-10-17

- Node 24.13.0 on Windows.
- `npm install --ignore-scripts`: success. Initial older Vite 7.2.2 had one high advisory; upgraded to registry-current pinned Vite 8.3.4.
- `npm audit --json` after update: exit 0, zero reported vulnerabilities (24 locally installed packages audited; report includes 67 dependency entries including optional platform packages).
- `npm run build`: strict TypeScript check and Vite production bundle passed. Initial TypeScript CSS-import error was resolved using Vite's CSS module declarations.
- Actual full browser workflow verification is owned by the repository integration test report. This file does not assert that unrun UI tests passed.

## Browser test interface

Accessible labels: Username, Password, Test title, Step 1, Step 2, Step 3, Step 4, Expected result. Buttons: Sign in; Create plan for review; Approve this plan; Run approved test; Sign out; Refresh plans and runs. Approval checkbox text begins “I confirm the interpreted actions”. Run status is an aria-live region with `data-testid="run-status"` on the verdict. Saved plan buttons include the title, author, approval state, and short ID.

## Limits

Four guided steps and one explicit expectation only; only the supplied local demo CRM is supported. No free-form AI interpretation, general editor, enterprise SSO, multiple tenants, persistence guarantee, accessibility certification, or enterprise browser certification is claimed. Run evidence is rendered as readable labelled observations; backend errors are displayed literally and escaped by React. Browser polling stops on terminal status, and uses a one-second delay while queued or running. Login errors and run failures are visible instead of fabricated success.
