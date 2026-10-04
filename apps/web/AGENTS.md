# apps/web notes for agents

This is a Next.js 16 App Router project. Its APIs changed from earlier versions, so check the docs in node_modules/next/dist/docs/ before assuming an API exists. Read ../../CLAUDE.md first: its rules apply here, including no em or en dashes anywhere, the self hosted Atkinson Hyperlegible Next only (the team's working notes (UPDATE 06) replaced the system font rule), no third party requests, and all user-facing strings from ../../content/locales/en.json.

Look and feel is set by docs/design/DESIGN.md and the team's working notes (UPDATE 06). Every colour, radius
and duration lives in styles/tokens.css; `npm run design-check` fails the build if one appears
anywhere else. Buttons, choices, photos, the gauge, the sheet and rows come from components/ui/.
