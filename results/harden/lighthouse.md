# Lighthouse

Measured 2026-09-23T04:51:48Z by `uv run python scripts/harden_lighthouse.py`, Lighthouse 13.5.0 in headless Chrome on this Mac (8 CPUs). Default mobile run, which is the throttled 4G profile: a mid-range phone screen, simulated 150 ms round trip at 1.6 Mbps down, CPU slowed four times. Three runs per page; the table shows the run with the median performance score, and the last column shows all three. Full reports stay outside the repo.

| Page | Perf | A11y | Best practices | SEO | FCP ms | LCP ms | TBT ms | CLS | SI ms | TTFB ms | Bytes | Perf, all runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production / | 97 | 100 | 100 | 100 | 836.0 | 2565.0 | 12 | 0 | 1694.0 | 46 | 232533 | 97, 97, 91 |
| production /judges | 99 | 100 | 100 | 100 | 908.0 | 1893.0 | 34 | 0 | 2804.0 | 140 | 1753217 | 99, 99, 99 |
| preview /city | 99 | 100 | 96 | 63 | 842.0 | 1883.0 | 26 | 0 | 2090.0 | 89 | 307804 | 99, 99, 99 |

Not measured, because they are not deployed there:

- production /city (https://second-look-79t.pages.dev/city): HTTP 404, not deployed
- production /walk (https://second-look-79t.pages.dev/walk): HTTP 404, not deployed
- preview /walk (https://depth.second-look-79t.pages.dev/walk): HTTP 404, not deployed

Lighthouse warnings:

- The page loaded too slowly to finish within the time limit. Results may be incomplete.
