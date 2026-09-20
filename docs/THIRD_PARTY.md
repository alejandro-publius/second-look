# Third party dependencies

Generated from uv.lock and apps/web/package-lock.json by `scripts/third_party.py` (W7). Until then this file lists the external services:

- Open-Meteo (https://open-meteo.com): rainfall lookups. Terms and attribution line to be recorded by W5 when the client is written.
- OneAquaHealth FHIR sandbox (https://sandbox.hl7europe.eu/oneaquahealth/fhir): read-only GETs at one per second, a tagged mirror of our own records when enabled.
- hl7-eu/oah implementation guide, commit b907cf0, built from source in CI. No LICENSE file in that repo, so nothing from it is redistributed here.
