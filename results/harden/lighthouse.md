# Lighthouse

Measured 2026-09-24T05:54:25Z by `uv run python scripts/harden_lighthouse.py`, Lighthouse 13.5.0 in headless Chrome on this Mac (8 CPUs). Default mobile run, which is the throttled 4G profile: a mid-range phone screen, simulated 150 ms round trip at 1.6 Mbps down, CPU slowed four times. Three runs per page; the table shows the run with the median performance score, and the last column shows all three. Full reports stay outside the repo.

| Page | Perf | A11y | Best practices | SEO | FCP ms | LCP ms | TBT ms | CLS | SI ms | TTFB ms | Bytes | Perf, all runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production / | 95 | 100 | 100 | 100 | 825.0 | 2870.0 | 6 | 0 | 2135.0 | 46 | 489609 | 95, 95, 95 |
| production /judges | 99 | 100 | 100 | 100 | 832.0 | 1799.0 | 22.0 | 0 | 2117.0 | 84 | 581788 | 99, 99, 99 |
| production /city | 99 | 100 | 100 | 100 | 827.0 | 2020.0 | 31 | 0 | 2112.0 | 67 | 489192 | 99, 99, 99 |
| preview /city | 99 | 100 | 100 | 63 | 850.0 | 1889.0 | 26 | 0 | 2103.0 | 60 | 308073 | 99, 99, 99 |
| production /walk | 99 | 100 | 100 | 100 | 836.0 | 1997.0 | 33 | 0 | 2159.0 | 84 | 1070651 | 79, 100, 99 |

Not measured, because they are not deployed there:

- preview /walk (https://depth.second-look-79t.pages.dev/walk): HTTP 404, not deployed

Lighthouse warnings:

- The page loaded too slowly to finish within the time limit. Results may be incomplete.
