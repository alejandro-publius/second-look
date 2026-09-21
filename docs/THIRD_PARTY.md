# Third party dependencies

Generated on 2026-09-21 by `uv run python scripts/third_party.py` from `uv.lock`, `apps/web/package-lock.json` and `worker/package-lock.json`. Do not edit by hand; rerun the script. Our own code is MIT; our photos and copy are CC BY 4.0 (README).

## External services

- Open-Meteo (https://open-meteo.com): rainfall lookups for the dry pipe rule in `core/rainfall.py`.
  Attribution shown wherever a rainfall figure appears: "Weather data by Open-Meteo.com, CC BY 4.0".
  Terms: https://open-meteo.com/en/terms (non-commercial use, fair rate limits, attribution).
  On any failure the app says "unknown" and skips the question; it never guesses.
- OneAquaHealth FHIR sandbox (https://sandbox.hl7europe.eu/oneaquahealth/fhir): read-only GETs at
  one per second with a user agent that names this repo, and a tagged mirror of our own records
  when `SANDBOX_MIRROR_ENABLED` is true. Conditional creates only, deletes by ledger id only.
- hl7-eu/oah implementation guide, commit b907cf0, built from source in CI with SUSHI 3.20.1 and
  validated with the HL7 validator. That repo has no LICENSE file, so nothing from it is
  redistributed here; `fhir/ig.lock` records the commit and the package sha256.
- Cloudflare Pages (web) and Cloudflare Workers with D1 (API) host the app (Update 09). What
  they log on their own is written in docs/DATA_HANDLING.md.
- The MCP server in `apps/mcp/` runs locally over stdio through the `mcp` Python SDK (MIT). It
  reads our own read only endpoint or a local export and calls no other service.

## Design references

Read during the design pass (docs/updates/UPDATE_06.md). Nothing is copied from either: no brand
colour, name, logo or font was taken. They informed structure and restraint only.

- Vercel Web Interface Guidelines, MIT
  (https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).
  `apps/web` was audited against every rule in it; the findings are in
  docs/reviews/DESIGN_REVIEW_01.md.
- VoltAgent awesome-design-md, MIT (https://github.com/VoltAgent/awesome-design-md). The Airbnb
  file for how a product lets photographs lead, the Wise file for how forms stay clear. Structure
  of docs/design/DESIGN.md borrows their shape: one read, tokens, components, do and do not.

## Fonts and icons

- Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono, Braille Institute, SIL Open Font
  License 1.1, through the `@fontsource-variable/atkinson-hyperlegible-next` and
  `@fontsource/atkinson-hyperlegible-mono` packages. Self hosted through `next/font/local`, so no
  request leaves our origin and `font-src 'self'` stays as it is.
- Phosphor Icons, MIT, through `@phosphor-icons/core` (a devDependency). Regular weight only.
  `apps/web/scripts/build-icons.mjs` generates `components/ui/Icon.tsx` from its SVG assets, so
  there is no icon runtime in the bundle and no second icon family can appear.

## Python packages (88, from uv.lock)

| Package | Version | License |
|---|---|---|
| alembic | 1.20.0 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anthropic | 1.7.0 | MIT |
| anyio | 4.15.1 | MIT |
| ast-serialize | 0.11.2 | MIT |
| attrs | 26.1.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | not installed here |
| contourpy | 1.4.0 | BSD-3-Clause |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause |
| cycler | 0.12.1 | BSD |
| docstring-parser | 0.18.0 | MIT |
| duckdb | 1.5.5 | MIT |
| fastapi | 0.141.1 | MIT |
| fonttools | 4.65.0 | MIT |
| greenlet | 3.5.6 | not installed here |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpcore2 | 2.13.0 | BSD-3-Clause |
| httptools | 0.8.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx2 | 2.13.0 | BSD-3-Clause |
| httpx2-jsfetch | 1.0 | not installed here |
| hypothesis | 6.168.0 | MPL-2.0 |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.0 | MIT |
| jiter | 0.17.0 | MIT |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| kiwisolver | 1.5.1 | BSD |
| librt | 0.15.0 | MIT |
| mako | 1.4.1 | MIT |
| markupsafe | 3.0.3 | BSD-3-Clause |
| matplotlib | 3.11.2 | Python Software Foundation |
| mcp | 2.2.0 | MIT |
| mcp-types | 2.2.0 | MIT |
| mypy | 2.3.1 | MIT |
| mypy-extensions | 1.1.0 | MIT |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| opentelemetry-api | 1.44.0 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pandas | 3.0.6 | BSD |
| pandas-stubs | 3.0.5.260914 | BSD-3-Clause |
| pathspec | 1.1.1 | Mozilla Public License 2.0 (MPL 2.0) |
| pillow | 12.3.0 | MIT-CMU |
| pluggy | 1.6.0 | MIT |
| psycopg | 3.3.6 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | LGPL-3.0-only |
| pycparser | 3.0 | BSD-3-Clause |
| pydantic | 2.13.5 | MIT |
| pydantic-core | 2.46.5 | MIT |
| pydantic-settings | 2.15.0 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pyjwt | 2.14.0 | MIT |
| pyparsing | 3.3.3 | MIT |
| pytest | 9.1.1 | MIT |
| pytest-asyncio | 1.4.0 | Apache-2.0 |
| python-dateutil | 2.9.0.post0 | Dual License |
| python-dotenv | 1.2.3 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| pywin32 | 312 | not installed here |
| pyyaml | 6.0.3 | MIT |
| referencing | 0.37.0 | MIT |
| respx | 0.23.1 | BSD-3-Clause |
| rpds-py | 2026.6.3 | MIT |
| ruff | 0.16.8 | MIT |
| scipy | 1.18.1 | BSD |
| six | 1.17.0 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 |
| sortedcontainers | 2.4.0 | Apache 2.0 |
| sqlalchemy | 2.0.54 | MIT |
| sqlmodel | 0.0.42 | MIT |
| sse-starlette | 3.4.11 | BSD-3-Clause |
| starlette | 1.6.0 | BSD-3-Clause |
| truststore | 0.10.4 | MIT |
| types-pyyaml | 6.0.12.20260906 | Apache-2.0 |
| types-requests | 2.33.0.20260906 | Apache-2.0 |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.4 | not installed here |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.53.0 | BSD-3-Clause |
| uvloop | 0.22.1 | MIT License |
| watchfiles | 1.2.0 | MIT |
| websockets | 17.1 | BSD-3-Clause |

## Web packages (438, from apps/web/package-lock.json)

dev = only used to build or test, not shipped to a browser.

| Package | Version | License | dev |
|---|---|---|---|
| @axe-core/playwright | 4.13.0 | MPL-2.0 | yes |
| @babel/code-frame | 7.29.7 | MIT | yes |
| @babel/compat-data | 7.29.7 | MIT | yes |
| @babel/core | 7.29.7 | MIT | yes |
| @babel/generator | 7.29.8 | MIT | yes |
| @babel/helper-compilation-targets | 7.29.7 | MIT | yes |
| @babel/helper-globals | 7.29.7 | MIT | yes |
| @babel/helper-module-imports | 7.29.7 | MIT | yes |
| @babel/helper-module-transforms | 7.29.7 | MIT | yes |
| @babel/helper-string-parser | 7.29.7 | MIT | yes |
| @babel/helper-validator-identifier | 7.29.7 | MIT | yes |
| @babel/helper-validator-option | 7.29.7 | MIT | yes |
| @babel/helpers | 7.29.7 | MIT | yes |
| @babel/parser | 7.29.9 | MIT | yes |
| @babel/template | 7.29.7 | MIT | yes |
| @babel/traverse | 7.29.8 | MIT | yes |
| @babel/types | 7.29.8 | MIT | yes |
| @emnapi/core | 1.10.0 | MIT | yes |
| @emnapi/runtime | 1.10.0 | MIT | yes |
| @emnapi/runtime | 1.11.3 | MIT |  |
| @emnapi/wasi-threads | 1.2.1 | MIT | yes |
| @eslint-community/eslint-utils | 4.10.1 | MIT | yes |
| @eslint-community/eslint-utils | 4.9.1 | MIT | yes |
| @eslint-community/regexpp | 4.12.2 | MIT | yes |
| @eslint/config-array | 0.21.2 | Apache-2.0 | yes |
| @eslint/config-helpers | 0.4.2 | Apache-2.0 | yes |
| @eslint/core | 0.17.0 | Apache-2.0 | yes |
| @eslint/eslintrc | 3.3.7 | MIT | yes |
| @eslint/js | 9.39.5 | MIT | yes |
| @eslint/object-schema | 2.1.7 | Apache-2.0 | yes |
| @eslint/plugin-kit | 0.4.1 | Apache-2.0 | yes |
| @fontsource-variable/atkinson-hyperlegible-next | 5.3.0 | OFL-1.1 |  |
| @fontsource/atkinson-hyperlegible-mono | 5.3.0 | OFL-1.1 |  |
| @humanfs/core | 0.19.2 | Apache-2.0 | yes |
| @humanfs/node | 0.16.8 | Apache-2.0 | yes |
| @humanfs/types | 0.15.0 | Apache-2.0 | yes |
| @humanwhocodes/module-importer | 1.0.1 | Apache-2.0 | yes |
| @humanwhocodes/retry | 0.4.3 | Apache-2.0 | yes |
| @img/colour | 1.1.0 | MIT |  |
| @img/sharp-darwin-arm64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-darwin-x64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-freebsd-wasm32 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-libvips-darwin-arm64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-darwin-x64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linux-arm | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linux-arm64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linux-ppc64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linux-riscv64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linux-s390x | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linux-x64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linuxmusl-arm64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-libvips-linuxmusl-x64 | 1.3.3 | LGPL-3.0-or-later |  |
| @img/sharp-linux-arm | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linux-arm64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linux-ppc64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linux-riscv64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linux-s390x | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linux-x64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linuxmusl-arm64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-linuxmusl-x64 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-wasm32 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later AND MIT |  |
| @img/sharp-webcontainers-wasm32 | 0.35.4 | Apache-2.0 |  |
| @img/sharp-win32-arm64 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later |  |
| @img/sharp-win32-ia32 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later |  |
| @img/sharp-win32-x64 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later |  |
| @jridgewell/gen-mapping | 0.3.13 | MIT | yes |
| @jridgewell/remapping | 2.3.5 | MIT | yes |
| @jridgewell/resolve-uri | 3.1.2 | MIT | yes |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT | yes |
| @jridgewell/trace-mapping | 0.3.31 | MIT | yes |
| @napi-rs/wasm-runtime | 1.2.4 | MIT | yes |
| @next/env | 16.3.5 | MIT |  |
| @next/eslint-plugin-next | 16.3.5 | MIT | yes |
| @next/swc-darwin-arm64 | 16.3.5 | MIT |  |
| @next/swc-darwin-x64 | 16.3.5 | MIT |  |
| @next/swc-linux-arm64-gnu | 16.3.5 | MIT |  |
| @next/swc-linux-arm64-musl | 16.3.5 | MIT |  |
| @next/swc-linux-x64-gnu | 16.3.5 | MIT |  |
| @next/swc-linux-x64-musl | 16.3.5 | MIT |  |
| @next/swc-win32-arm64-msvc | 16.3.5 | MIT |  |
| @next/swc-win32-x64-msvc | 16.3.5 | MIT |  |
| @nodelib/fs.scandir | 2.1.5 | MIT | yes |
| @nodelib/fs.stat | 2.0.5 | MIT | yes |
| @nodelib/fs.walk | 1.2.8 | MIT | yes |
| @nolyfill/is-core-module | 1.0.39 | MIT | yes |
| @phosphor-icons/core | 2.1.1 | MIT | yes |
| @playwright/test | 1.63.0 | Apache-2.0 |  |
| @rtsao/scc | 1.1.0 | MIT | yes |
| @swc/helpers | 0.5.23 | Apache-2.0 |  |
| @tybys/wasm-util | 0.10.4 | MIT | yes |
| @types/estree | 1.0.9 | MIT | yes |
| @types/js-yaml | 4.0.9 | MIT | yes |
| @types/json-schema | 7.0.15 | MIT | yes |
| @types/json5 | 0.0.29 | MIT | yes |
| @types/node | 20.19.43 | MIT | yes |
| @types/qrcode | 1.5.6 | MIT | yes |
| @types/react | 19.3.0 | MIT | yes |
| @types/react-dom | 19.3.0 | MIT | yes |
| @typescript-eslint/eslint-plugin | 8.70.0 | MIT | yes |
| @typescript-eslint/parser | 8.70.0 | MIT | yes |
| @typescript-eslint/project-service | 8.70.0 | MIT | yes |
| @typescript-eslint/scope-manager | 8.70.0 | MIT | yes |
| @typescript-eslint/tsconfig-utils | 8.70.0 | MIT | yes |
| @typescript-eslint/type-utils | 8.70.0 | MIT | yes |
| @typescript-eslint/types | 8.70.0 | MIT | yes |
| @typescript-eslint/typescript-estree | 8.70.0 | MIT | yes |
| @typescript-eslint/utils | 8.70.0 | MIT | yes |
| @typescript-eslint/visitor-keys | 8.70.0 | MIT | yes |
| @unrs/resolver-binding-android-arm-eabi | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-android-arm64 | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-darwin-arm64 | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-darwin-x64 | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-freebsd-x64 | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-arm-gnueabihf | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-arm-musleabihf | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-arm64-gnu | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-arm64-musl | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-loong64-gnu | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-loong64-musl | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-ppc64-gnu | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-riscv64-gnu | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-riscv64-musl | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-s390x-gnu | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-x64-gnu | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-linux-x64-musl | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-openharmony-arm64 | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-wasm32-wasi | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-win32-arm64-msvc | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-win32-ia32-msvc | 1.12.2 | MIT | yes |
| @unrs/resolver-binding-win32-x64-msvc | 1.12.2 | MIT | yes |
| acorn | 8.18.0 | MIT | yes |
| acorn-jsx | 5.3.2 | MIT | yes |
| ajv | 6.15.0 | MIT | yes |
| ansi-regex | 5.0.1 | MIT |  |
| ansi-styles | 4.3.0 | MIT |  |
| argparse | 2.0.1 | Python-2.0 |  |
| aria-query | 5.3.2 | Apache-2.0 | yes |
| array-buffer-byte-length | 1.0.2 | MIT | yes |
| array-includes | 3.2.0 | MIT | yes |
| array.prototype.findlast | 1.2.5 | MIT | yes |
| array.prototype.findlastindex | 1.2.6 | MIT | yes |
| array.prototype.flat | 1.3.3 | MIT | yes |
| array.prototype.flatmap | 1.3.3 | MIT | yes |
| array.prototype.tosorted | 1.1.4 | MIT | yes |
| arraybuffer.prototype.slice | 1.0.4 | MIT | yes |
| ast-types-flow | 0.0.8 | MIT | yes |
| async-function | 1.0.0 | MIT | yes |
| available-typed-arrays | 1.0.7 | MIT | yes |
| axe-core | 4.13.0 | MPL-2.0 | yes |
| axobject-query | 4.1.0 | Apache-2.0 | yes |
| balanced-match | 1.0.2 | MIT | yes |
| balanced-match | 4.0.4 | MIT | yes |
| baseline-browser-mapping | 2.11.25 | Apache-2.0 |  |
| brace-expansion | 1.1.21 | MIT | yes |
| brace-expansion | 5.0.12 | MIT | yes |
| braces | 3.0.3 | MIT | yes |
| browserslist | 4.29.0 | MIT | yes |
| call-bind | 1.0.9 | MIT | yes |
| call-bind-apply-helpers | 1.0.2 | MIT | yes |
| call-bound | 1.0.4 | MIT | yes |
| callsites | 3.1.0 | MIT | yes |
| camelcase | 5.3.1 | MIT |  |
| caniuse-lite | 1.0.30001810 | CC-BY-4.0 |  |
| chalk | 4.1.2 | MIT | yes |
| client-only | 0.0.1 | MIT |  |
| cliui | 6.0.0 | ISC |  |
| color-convert | 2.0.1 | MIT |  |
| color-name | 1.1.4 | MIT |  |
| concat-map | 0.0.1 | MIT | yes |
| convert-source-map | 2.0.0 | MIT | yes |
| cross-spawn | 7.0.6 | MIT | yes |
| csstype | 3.2.3 | MIT | yes |
| damerau-levenshtein | 1.0.8 | BSD-2-Clause | yes |
| data-view-buffer | 1.0.2 | MIT | yes |
| data-view-byte-length | 1.0.2 | MIT | yes |
| data-view-byte-offset | 1.0.1 | MIT | yes |
| debug | 3.2.7 | MIT | yes |
| debug | 3.2.7 | MIT | yes |
| debug | 3.2.7 | MIT | yes |
| debug | 4.4.3 | MIT | yes |
| decamelize | 1.2.0 | MIT |  |
| deep-is | 0.1.4 | MIT | yes |
| define-data-property | 1.1.4 | MIT | yes |
| define-properties | 1.2.1 | MIT | yes |
| detect-libc | 2.1.2 | Apache-2.0 |  |
| dijkstrajs | 1.0.3 | MIT |  |
| doctrine | 2.1.0 | Apache-2.0 | yes |
| dunder-proto | 1.0.1 | MIT | yes |
| electron-to-chromium | 1.5.433 | ISC | yes |
| emoji-regex | 8.0.0 | MIT |  |
| emoji-regex | 9.2.2 | MIT | yes |
| es-abstract | 1.24.2 | MIT | yes |
| es-abstract-get | 1.0.0 | MIT | yes |
| es-define-property | 1.0.1 | MIT | yes |
| es-errors | 1.3.0 | MIT | yes |
| es-iterator-helpers | 1.4.0 | MIT | yes |
| es-object-atoms | 1.1.2 | MIT | yes |
| es-set-tostringtag | 2.1.0 | MIT | yes |
| es-shim-unscopables | 1.1.0 | MIT | yes |
| es-to-primitive | 1.3.4 | MIT | yes |
| escalade | 3.2.0 | MIT | yes |
| escape-string-regexp | 4.0.0 | MIT | yes |
| eslint | 9.39.5 | MIT | yes |
| eslint-config-next | 16.3.5 | MIT | yes |
| eslint-import-resolver-node | 0.3.10 | MIT | yes |
| eslint-import-resolver-typescript | 3.10.1 | ISC | yes |
| eslint-module-utils | 2.14.0 | MIT | yes |
| eslint-plugin-import | 2.32.0 | MIT | yes |
| eslint-plugin-jsx-a11y | 6.10.2 | MIT | yes |
| eslint-plugin-react | 7.37.5 | MIT | yes |
| eslint-plugin-react-hooks | 7.1.1 | MIT | yes |
| eslint-scope | 8.4.0 | BSD-2-Clause | yes |
| eslint-visitor-keys | 3.4.3 | Apache-2.0 | yes |
| eslint-visitor-keys | 3.4.3 | Apache-2.0 | yes |
| eslint-visitor-keys | 4.2.1 | Apache-2.0 | yes |
| eslint-visitor-keys | 5.0.1 | Apache-2.0 | yes |
| espree | 10.4.0 | BSD-2-Clause | yes |
| esquery | 1.7.0 | BSD-3-Clause | yes |
| esrecurse | 4.3.0 | BSD-2-Clause | yes |
| estraverse | 5.3.0 | BSD-2-Clause | yes |
| esutils | 2.0.3 | BSD-2-Clause | yes |
| fast-deep-equal | 3.1.3 | MIT | yes |
| fast-glob | 3.3.1 | MIT | yes |
| fast-json-stable-stringify | 2.1.0 | MIT | yes |
| fast-levenshtein | 2.0.6 | MIT | yes |
| fastq | 1.20.3 | ISC | yes |
| fdir | 6.5.0 | MIT | yes |
| file-entry-cache | 8.0.0 | MIT | yes |
| fill-range | 7.1.1 | MIT | yes |
| find-up | 4.1.0 | MIT |  |
| find-up | 5.0.0 | MIT | yes |
| flat-cache | 4.0.1 | MIT | yes |
| flatted | 3.4.4 | ISC | yes |
| for-each | 0.3.5 | MIT | yes |
| function-bind | 1.1.2 | MIT | yes |
| function.prototype.name | 1.2.0 | MIT | yes |
| functions-have-names | 1.2.3 | MIT | yes |
| generator-function | 2.0.1 | MIT | yes |
| gensync | 1.0.0-beta.2 | MIT | yes |
| get-caller-file | 2.0.5 | ISC |  |
| get-intrinsic | 1.3.0 | MIT | yes |
| get-proto | 1.0.1 | MIT | yes |
| get-symbol-description | 1.1.0 | MIT | yes |
| get-tsconfig | 4.14.3 | MIT | yes |
| glob-parent | 5.1.2 | ISC | yes |
| glob-parent | 6.0.2 | ISC | yes |
| globals | 14.0.0 | MIT | yes |
| globals | 16.4.0 | MIT | yes |
| globalthis | 1.0.4 | MIT | yes |
| gopd | 1.2.0 | MIT | yes |
| has-bigints | 1.1.0 | MIT | yes |
| has-flag | 4.0.0 | MIT | yes |
| has-property-descriptors | 1.0.2 | MIT | yes |
| has-proto | 1.2.0 | MIT | yes |
| has-symbols | 1.1.0 | MIT | yes |
| has-tostringtag | 1.0.2 | MIT | yes |
| hasown | 2.0.4 | MIT | yes |
| hermes-estree | 0.25.1 | MIT | yes |
| hermes-parser | 0.25.1 | MIT | yes |
| ignore | 5.3.2 | MIT | yes |
| ignore | 7.0.9 | MIT | yes |
| import-fresh | 3.3.1 | MIT | yes |
| imurmurhash | 0.1.4 | MIT | yes |
| internal-slot | 1.1.0 | MIT | yes |
| is-array-buffer | 3.0.5 | MIT | yes |
| is-async-function | 2.1.1 | MIT | yes |
| is-bigint | 1.1.0 | MIT | yes |
| is-boolean-object | 1.2.2 | MIT | yes |
| is-bun-module | 2.0.0 | MIT | yes |
| is-callable | 1.2.7 | MIT | yes |
| is-core-module | 2.17.0 | MIT | yes |
| is-data-view | 1.0.2 | MIT | yes |
| is-date-object | 1.1.0 | MIT | yes |
| is-document.all | 1.0.0 | MIT | yes |
| is-extglob | 2.1.1 | MIT | yes |
| is-finalizationregistry | 1.1.1 | MIT | yes |
| is-fullwidth-code-point | 3.0.0 | MIT |  |
| is-generator-function | 1.1.2 | MIT | yes |
| is-glob | 4.0.3 | MIT | yes |
| is-map | 2.0.3 | MIT | yes |
| is-negative-zero | 2.0.3 | MIT | yes |
| is-number | 7.0.0 | MIT | yes |
| is-number-object | 1.1.1 | MIT | yes |
| is-regex | 1.2.1 | MIT | yes |
| is-set | 2.0.3 | MIT | yes |
| is-shared-array-buffer | 1.0.4 | MIT | yes |
| is-string | 1.1.1 | MIT | yes |
| is-symbol | 1.1.1 | MIT | yes |
| is-typed-array | 1.1.15 | MIT | yes |
| is-weakmap | 2.0.2 | MIT | yes |
| is-weakref | 1.1.1 | MIT | yes |
| is-weakset | 2.0.4 | MIT | yes |
| isarray | 2.0.5 | MIT | yes |
| isexe | 2.0.0 | ISC | yes |
| iterator.prototype | 1.1.5 | MIT | yes |
| js-tokens | 4.0.0 | MIT | yes |
| js-yaml | 4.3.2 | MIT | yes |
| js-yaml | 5.4.2 | MIT |  |
| jsesc | 3.1.0 | MIT | yes |
| json-buffer | 3.0.1 | MIT | yes |
| json-schema-traverse | 0.4.1 | MIT | yes |
| json-stable-stringify-without-jsonify | 1.0.1 | MIT | yes |
| json5 | 1.0.2 | MIT | yes |
| json5 | 2.2.3 | MIT | yes |
| jsx-ast-utils | 3.3.5 | MIT | yes |
| keyv | 4.5.4 | MIT | yes |
| language-subtag-registry | 0.3.23 | CC0-1.0 | yes |
| language-tags | 1.0.9 | MIT | yes |
| levn | 0.4.1 | MIT | yes |
| locate-path | 5.0.0 | MIT |  |
| locate-path | 6.0.0 | MIT | yes |
| lodash.merge | 4.6.2 | MIT | yes |
| loose-envify | 1.4.0 | MIT | yes |
| lru-cache | 5.1.1 | ISC | yes |
| math-intrinsics | 1.1.0 | MIT | yes |
| merge2 | 1.4.1 | MIT | yes |
| micromatch | 4.0.8 | MIT | yes |
| minimatch | 10.2.6 | BlueOak-1.0.0 | yes |
| minimatch | 3.1.5 | ISC | yes |
| minimist | 1.2.8 | MIT | yes |
| ms | 2.1.3 | MIT | yes |
| nanoid | 3.3.19 | MIT |  |
| napi-postinstall | 0.3.4 | MIT | yes |
| natural-compare | 1.4.0 | MIT | yes |
| next | 16.3.5 | MIT |  |
| node-exports-info | 1.6.2 | MIT | yes |
| node-releases | 2.0.56 | MIT | yes |
| object-assign | 4.1.1 | MIT | yes |
| object-inspect | 1.13.4 | MIT | yes |
| object-keys | 1.1.1 | MIT | yes |
| object.assign | 4.1.7 | MIT | yes |
| object.entries | 1.1.9 | MIT | yes |
| object.fromentries | 2.0.8 | MIT | yes |
| object.groupby | 1.0.3 | MIT | yes |
| object.values | 1.2.1 | MIT | yes |
| optionator | 0.9.4 | MIT | yes |
| own-keys | 1.0.2 | MIT | yes |
| p-limit | 2.3.0 | MIT |  |
| p-limit | 3.1.0 | MIT | yes |
| p-locate | 4.1.0 | MIT |  |
| p-locate | 5.0.0 | MIT | yes |
| p-try | 2.2.0 | MIT |  |
| parent-module | 1.0.1 | MIT | yes |
| path-exists | 4.0.0 | MIT |  |
| path-key | 3.1.1 | MIT | yes |
| path-parse | 1.0.7 | MIT | yes |
| picocolors | 1.1.1 | ISC |  |
| picomatch | 2.3.2 | MIT | yes |
| picomatch | 4.0.7 | MIT | yes |
| playwright | 1.63.0 | Apache-2.0 |  |
| playwright-core | 1.63.0 | Apache-2.0 |  |
| pngjs | 5.0.0 | MIT |  |
| possible-typed-array-names | 1.1.0 | MIT | yes |
| postcss | 8.5.23 | MIT |  |
| prelude-ls | 1.2.1 | MIT | yes |
| prop-types | 15.8.1 | MIT | yes |
| punycode | 2.3.1 | MIT | yes |
| qrcode | 1.5.4 | MIT |  |
| queue-microtask | 1.2.3 | MIT | yes |
| react | 19.2.8 | MIT |  |
| react-dom | 19.2.8 | MIT |  |
| react-is | 16.13.1 | MIT | yes |
| reflect.getprototypeof | 1.0.10 | MIT | yes |
| regexp.prototype.flags | 1.5.4 | MIT | yes |
| require-directory | 2.1.1 | MIT |  |
| require-main-filename | 2.0.0 | ISC |  |
| resolve | 2.0.0-next.7 | MIT | yes |
| resolve-from | 4.0.0 | MIT | yes |
| resolve-pkg-maps | 1.0.0 | MIT | yes |
| reusify | 1.1.0 | MIT | yes |
| run-parallel | 1.2.0 | MIT | yes |
| safe-array-concat | 1.1.4 | MIT | yes |
| safe-push-apply | 1.0.0 | MIT | yes |
| safe-regex-test | 1.1.0 | MIT | yes |
| scheduler | 0.27.0 | MIT |  |
| semver | 6.3.1 | ISC | yes |
| semver | 7.8.5 | ISC | yes |
| semver | 7.8.5 | ISC | yes |
| semver | 7.8.5 | ISC |  |
| set-blocking | 2.0.0 | ISC |  |
| set-function-length | 1.2.2 | MIT | yes |
| set-function-name | 2.0.2 | MIT | yes |
| set-proto | 1.0.0 | MIT | yes |
| sharp | 0.35.4 | Apache-2.0 |  |
| shebang-command | 2.0.0 | MIT | yes |
| shebang-regex | 3.0.0 | MIT | yes |
| side-channel | 1.1.1 | MIT | yes |
| side-channel-list | 1.0.1 | MIT | yes |
| side-channel-map | 1.0.1 | MIT | yes |
| side-channel-weakmap | 1.0.2 | MIT | yes |
| source-map-js | 1.2.1 | BSD-3-Clause |  |
| stable-hash | 0.0.5 | MIT | yes |
| stop-iteration-iterator | 1.1.0 | MIT | yes |
| string-width | 4.2.3 | MIT |  |
| string.prototype.includes | 2.0.1 | MIT | yes |
| string.prototype.matchall | 4.1.0 | MIT | yes |
| string.prototype.repeat | 1.0.0 | MIT | yes |
| string.prototype.trim | 1.2.11 | MIT | yes |
| string.prototype.trimend | 1.0.10 | MIT | yes |
| string.prototype.trimstart | 1.0.8 | MIT | yes |
| strip-ansi | 6.0.1 | MIT |  |
| strip-bom | 3.0.0 | MIT | yes |
| strip-json-comments | 3.1.1 | MIT | yes |
| styled-jsx | 5.1.6 | MIT |  |
| supports-color | 7.2.0 | MIT | yes |
| supports-preserve-symlinks-flag | 1.0.0 | MIT | yes |
| tinyglobby | 0.2.17 | MIT | yes |
| to-regex-range | 5.0.1 | MIT | yes |
| ts-api-utils | 2.5.0 | MIT | yes |
| tsconfig-paths | 3.15.0 | MIT | yes |
| tslib | 2.8.1 | 0BSD |  |
| type-check | 0.4.0 | MIT | yes |
| typed-array-buffer | 1.0.3 | MIT | yes |
| typed-array-byte-length | 1.0.3 | MIT | yes |
| typed-array-byte-offset | 1.0.5 | MIT | yes |
| typed-array-length | 1.0.8 | MIT | yes |
| typescript | 5.9.3 | Apache-2.0 | yes |
| typescript-eslint | 8.70.0 | MIT | yes |
| unbox-primitive | 1.1.0 | MIT | yes |
| undici-types | 6.21.0 | MIT | yes |
| unrs-resolver | 1.12.2 | MIT | yes |
| update-browserslist-db | 1.3.3 | MIT | yes |
| uri-js | 4.4.1 | BSD-2-Clause | yes |
| which | 2.0.2 | ISC | yes |
| which-boxed-primitive | 1.1.1 | MIT | yes |
| which-builtin-type | 1.2.1 | MIT | yes |
| which-collection | 1.0.2 | MIT | yes |
| which-module | 2.0.1 | ISC |  |
| which-typed-array | 1.1.24 | MIT | yes |
| word-wrap | 1.2.5 | MIT | yes |
| wrap-ansi | 6.2.0 | MIT |  |
| y18n | 4.0.3 | ISC |  |
| yallist | 3.1.1 | ISC | yes |
| yargs | 15.4.1 | MIT |  |
| yargs-parser | 18.1.3 | ISC |  |
| yocto-queue | 0.1.0 | MIT | yes |
| zod | 4.6.5 | MIT | yes |
| zod-validation-error | 4.0.2 | MIT | yes |

## Worker packages (120, from worker/package-lock.json)

All dev: the toolchain that type checks, tests and runs the Worker locally. The deployed Worker bundles only our own code and worker/src/content.json.

| Package | Version | License | dev |
|---|---|---|---|
| @cloudflare/kv-asset-handler | 0.5.0 | MIT OR Apache-2.0 | yes |
| @cloudflare/unenv-preset | 2.16.1 | MIT OR Apache-2.0 | yes |
| @cloudflare/workerd-darwin-64 | 1.20260918.1 | Apache-2.0 | yes |
| @cloudflare/workerd-darwin-arm64 | 1.20260918.1 | Apache-2.0 | yes |
| @cloudflare/workerd-linux-64 | 1.20260918.1 | Apache-2.0 | yes |
| @cloudflare/workerd-linux-arm64 | 1.20260918.1 | Apache-2.0 | yes |
| @cloudflare/workerd-windows-64 | 1.20260918.1 | Apache-2.0 | yes |
| @cloudflare/workers-types | 5.20260921.1 | MIT OR Apache-2.0 | yes |
| @cspotcode/source-map-support | 0.8.1 | MIT | yes |
| @emnapi/runtime | 1.11.3 | MIT | yes |
| @esbuild/aix-ppc64 | 0.28.1 | MIT | yes |
| @esbuild/aix-ppc64 | 0.28.2 | MIT | yes |
| @esbuild/android-arm | 0.28.1 | MIT | yes |
| @esbuild/android-arm | 0.28.2 | MIT | yes |
| @esbuild/android-arm64 | 0.28.1 | MIT | yes |
| @esbuild/android-arm64 | 0.28.2 | MIT | yes |
| @esbuild/android-x64 | 0.28.1 | MIT | yes |
| @esbuild/android-x64 | 0.28.2 | MIT | yes |
| @esbuild/darwin-arm64 | 0.28.1 | MIT | yes |
| @esbuild/darwin-arm64 | 0.28.2 | MIT | yes |
| @esbuild/darwin-x64 | 0.28.1 | MIT | yes |
| @esbuild/darwin-x64 | 0.28.2 | MIT | yes |
| @esbuild/freebsd-arm64 | 0.28.1 | MIT | yes |
| @esbuild/freebsd-arm64 | 0.28.2 | MIT | yes |
| @esbuild/freebsd-x64 | 0.28.1 | MIT | yes |
| @esbuild/freebsd-x64 | 0.28.2 | MIT | yes |
| @esbuild/linux-arm | 0.28.1 | MIT | yes |
| @esbuild/linux-arm | 0.28.2 | MIT | yes |
| @esbuild/linux-arm64 | 0.28.1 | MIT | yes |
| @esbuild/linux-arm64 | 0.28.2 | MIT | yes |
| @esbuild/linux-ia32 | 0.28.1 | MIT | yes |
| @esbuild/linux-ia32 | 0.28.2 | MIT | yes |
| @esbuild/linux-loong64 | 0.28.1 | MIT | yes |
| @esbuild/linux-loong64 | 0.28.2 | MIT | yes |
| @esbuild/linux-mips64el | 0.28.1 | MIT | yes |
| @esbuild/linux-mips64el | 0.28.2 | MIT | yes |
| @esbuild/linux-ppc64 | 0.28.1 | MIT | yes |
| @esbuild/linux-ppc64 | 0.28.2 | MIT | yes |
| @esbuild/linux-riscv64 | 0.28.1 | MIT | yes |
| @esbuild/linux-riscv64 | 0.28.2 | MIT | yes |
| @esbuild/linux-s390x | 0.28.1 | MIT | yes |
| @esbuild/linux-s390x | 0.28.2 | MIT | yes |
| @esbuild/linux-x64 | 0.28.1 | MIT | yes |
| @esbuild/linux-x64 | 0.28.2 | MIT | yes |
| @esbuild/netbsd-arm64 | 0.28.1 | MIT | yes |
| @esbuild/netbsd-arm64 | 0.28.2 | MIT | yes |
| @esbuild/netbsd-x64 | 0.28.1 | MIT | yes |
| @esbuild/netbsd-x64 | 0.28.2 | MIT | yes |
| @esbuild/openbsd-arm64 | 0.28.1 | MIT | yes |
| @esbuild/openbsd-arm64 | 0.28.2 | MIT | yes |
| @esbuild/openbsd-x64 | 0.28.1 | MIT | yes |
| @esbuild/openbsd-x64 | 0.28.2 | MIT | yes |
| @esbuild/openharmony-arm64 | 0.28.1 | MIT | yes |
| @esbuild/openharmony-arm64 | 0.28.2 | MIT | yes |
| @esbuild/sunos-x64 | 0.28.1 | MIT | yes |
| @esbuild/sunos-x64 | 0.28.2 | MIT | yes |
| @esbuild/win32-arm64 | 0.28.1 | MIT | yes |
| @esbuild/win32-arm64 | 0.28.2 | MIT | yes |
| @esbuild/win32-ia32 | 0.28.1 | MIT | yes |
| @esbuild/win32-ia32 | 0.28.2 | MIT | yes |
| @esbuild/win32-x64 | 0.28.1 | MIT | yes |
| @esbuild/win32-x64 | 0.28.2 | MIT | yes |
| @img/colour | 1.1.0 | MIT | yes |
| @img/sharp-darwin-arm64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-darwin-x64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-freebsd-wasm32 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-libvips-darwin-arm64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-darwin-x64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linux-arm | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linux-arm64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linux-ppc64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linux-riscv64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linux-s390x | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linux-x64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linuxmusl-arm64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-libvips-linuxmusl-x64 | 1.3.3 | LGPL-3.0-or-later | yes |
| @img/sharp-linux-arm | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linux-arm64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linux-ppc64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linux-riscv64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linux-s390x | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linux-x64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linuxmusl-arm64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-linuxmusl-x64 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-wasm32 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later AND MIT | yes |
| @img/sharp-webcontainers-wasm32 | 0.35.4 | Apache-2.0 | yes |
| @img/sharp-win32-arm64 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | yes |
| @img/sharp-win32-ia32 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | yes |
| @img/sharp-win32-x64 | 0.35.4 | Apache-2.0 AND LGPL-3.0-or-later | yes |
| @jridgewell/resolve-uri | 3.1.2 | MIT | yes |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT | yes |
| @jridgewell/trace-mapping | 0.3.9 | MIT | yes |
| @poppinss/colors | 4.1.6 | MIT | yes |
| @poppinss/dumper | 0.6.5 | MIT | yes |
| @poppinss/exception | 1.2.3 | MIT | yes |
| @sindresorhus/is | 7.2.0 | MIT | yes |
| @speed-highlight/core | 1.2.24 | CC0-1.0 | yes |
| blake3-wasm | 2.1.5 | MIT | yes |
| cookie | 1.1.1 | MIT | yes |
| detect-libc | 2.1.2 | Apache-2.0 | yes |
| error-stack-parser-es | 1.0.5 | MIT | yes |
| esbuild | 0.28.1 | MIT | yes |
| esbuild | 0.28.2 | MIT | yes |
| fsevents | 2.3.3 | MIT | yes |
| kleur | 4.1.5 | MIT | yes |
| miniflare | 5.20260918.0-alpha | MIT | yes |
| path-to-regexp | 6.3.0 | MIT | yes |
| pathe | 2.0.3 | MIT | yes |
| semver | 7.8.5 | ISC | yes |
| sharp | 0.35.4 | Apache-2.0 | yes |
| supports-color | 10.2.2 | MIT | yes |
| tslib | 2.8.1 | 0BSD | yes |
| typescript | 5.9.3 | Apache-2.0 | yes |
| undici | 7.29.0 | MIT | yes |
| unenv | 2.0.0-rc.24 | MIT | yes |
| workerd | 1.20260918.1 | Apache-2.0 | yes |
| wrangler | 4.135.0 | MIT OR Apache-2.0 | yes |
| ws | 8.21.0 | MIT | yes |
| youch | 4.1.0-beta.10 | MIT | yes |
| youch-core | 0.3.3 | MIT | yes |

Licenses not found for 5 Python and 0 web and worker packages; check those by hand before the repo goes public.
