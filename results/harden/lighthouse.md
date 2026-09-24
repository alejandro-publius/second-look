# Lighthouse

Measured 2026-09-24T10:03:26Z by `uv run python scripts/harden_lighthouse.py`, Lighthouse 13.5.0 in headless Chrome on this Mac (8 CPUs). Default mobile run, which is the throttled 4G profile: a mid-range phone screen, simulated 150 ms round trip at 1.6 Mbps down, CPU slowed four times. Three runs per page; the table shows the run with the median performance score, and the last column shows all three. Full reports stay outside the repo.

| Page | Perf | A11y | Best practices | SEO | FCP ms | LCP ms | TBT ms | CLS | SI ms | TTFB ms | Bytes | Perf, all runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production / | 95 | 100 | 100 | 100 | 869.0 | 2682.0 | 18.0 | 0 | 3502.0 | 43 | 410028 | 95, 98, 95 |
| production /t | 99 | 100 | 100 | 100 | 854.0 | 2036.0 | 51 | 0 | 2110.0 | 80 | 403701 | 99, 99, 99 |
| production /demo | 99 | 100 | 100 | 100 | 821.0 | 1863.0 | 29 | 0 | 2077.0 | 53 | 408569 | 100, 96, 99 |
| production /judges | 99 | 100 | 100 | 100 | 848.0 | 1816.0 | 24.0 | 0 | 2087.0 | 54 | 518071 | 99, 99, 99 |
| production /check | 99 | 100 | 100 | 100 | 832.0 | 2024.0 | 29 | 0 | 2105.0 | 74 | 404227 | 99, 100, 99 |
| production /spot | 99 | 100 | 96 | 100 | 818.0 | 2011.0 | 15.0 | 0 | 818.0 | 52 | 397960 | 99, 99, 100 |
| production /quick | 100 | 100 | 100 | 100 | 818.0 | 1110.0 | 14.0 | 0 | 818.0 | 53 | 399269 | 99, 100, 100 |
| production /two | 99 | 100 | 100 | 100 | 851.0 | 1891.0 | 31 | 0 | 2130.0 | 71 | 396631 | 99, 99, 99 |
| production /poster | 96 | 100 | 100 | 100 | 906.0 | 2791.0 | 47 | 0 | 2190.0 | 60 | 372773 | 96, 98, 96 |
| production /how-we-know | 99 | 100 | 100 | 100 | 835.0 | 1804.0 | 24.0 | 0 | 2101.0 | 70 | 372251 | 99, 99, 100 |
| production /about | 99 | 100 | 100 | 100 | 846.0 | 1810.0 | 20.0 | 0 | 2109.0 | 70 | 433807 | 99, 99, 99 |
| production /privacy | 99 | 100 | 100 | 100 | 826.0 | 1794.0 | 24 | 0 | 2072.0 | 71 | 372540 | 99, 100, 99 |
| production /credits | 99 | 100 | 100 | 100 | 843.0 | 1799.0 | 23 | 0 | 2084.0 | 61 | 377152 | 99, 99, 100 |
| production /offline | 99 | 100 | 100 | 100 | 842.0 | 2196.0 | 45 | 0 | 2138.0 | 67 | 408785 | 99, 99, 100 |
| production /share/12 | 99 | 100 | 100 | 100 | 843.0 | 1801.0 | 40 | 0 | 2092.0 | 53 | 411984 | 99, 100, 97 |
| production /accessibility | 100 | 100 | 100 | 100 | 830.0 | 1789.0 | 12.0 | 0 | 2078.0 | 58 | 372402 | 100, 100, 99 |
| production /verify | 99 | 100 | 100 | 100 | 968.0 | 2018.0 | 23 | 0 | 2142.0 | 78 | 409167 | 99, 99, 100 |
| production /city?creek=strawberry-creek | 99 | 100 | 100 | 100 | 842.0 | 2029.0 | 26 | 0 | 2092.0 | 74 | 411193 | 99, 99, 99 |
| production /walk | 97 | 100 | 100 | 100 | 855.0 | 2494.0 | 47 | 0 | 2363.0 | 66 | 991055 | 99, 97, 93 |
| production /walk/v02 | 94 | 100 | 100 | 100 | 846.0 | 3049.0 | 3 | 0 | 2198.0 | 69 | 482249 | 94, 94, 97 |

Not measured, because they are not deployed there:


Lighthouse warnings:

- The page loaded too slowly to finish within the time limit. Results may be incomplete.
