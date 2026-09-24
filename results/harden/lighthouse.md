# Lighthouse

Measured 2026-09-24T13:48:38Z by `uv run python scripts/harden_lighthouse.py`, Lighthouse 13.5.0 in headless Chrome on this Mac (8 CPUs). Default mobile run, which is the throttled 4G profile: a mid-range phone screen, simulated 150 ms round trip at 1.6 Mbps down, CPU slowed four times. Three runs per page; the table shows the run with the median performance score, and the last column shows all three. Full reports stay outside the repo.

| Page | Perf | A11y | Best practices | SEO | FCP ms | LCP ms | TBT ms | CLS | SI ms | TTFB ms | Bytes | Perf, all runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production / | 93 | 100 | 100 | 100 | 865.0 | 3075.0 | 50 | 0 | 3559.0 | 79 | 411684 | 95, 93, 93 |
| production /t | 99 | 100 | 100 | 100 | 821.0 | 2011.0 | 18.0 | 0 | 821.0 | 60 | 406046 | 99, 99, 99 |
| production /demo | 99 | 100 | 100 | 100 | 854.0 | 2036.0 | 84 | 0 | 2192.0 | 77 | 411393 | 99, 99, 99 |
| production /judges | 99 | 100 | 100 | 100 | 890.0 | 1865.0 | 44 | 0 | 2107.0 | 54 | 450384 | 99, 99, 99 |
| production /check | 99 | 100 | 100 | 100 | 830.0 | 2019.0 | 53 | 0 | 2121.0 | 69 | 405742 | 99, 95, 99 |
| production /spot | 99 | 100 | 100 | 100 | 847.0 | 1881.0 | 61 | 0 | 2140.0 | 61 | 399164 | 100, 99, 99 |
| production /quick | 99 | 100 | 100 | 100 | 828.0 | 1864.0 | 49 | 0 | 2118.0 | 65 | 400963 | 99, 99, 99 |
| production /two | 99 | 100 | 100 | 100 | 824.0 | 1862.0 | 16.0 | 0 | 2079.0 | 72 | 398453 | 99, 99, 99 |
| production /poster | 96 | 100 | 100 | 100 | 845.0 | 2731.0 | 46.0 | 0 | 2175.0 | 49 | 373280 | 98, 96, 96 |
| production /how-we-know | 99 | 100 | 100 | 100 | 1305.0 | 1972.0 | 25 | 0 | 2456.0 | 63 | 385079 | 99, 100, 99 |
| production /about | 100 | 100 | 100 | 100 | 839.0 | 1130.0 | 12.0 | 0 | 839.0 | 63 | 444043 | 100, 100, 100 |
| production /privacy | 100 | 100 | 100 | 100 | 825.0 | 1115.0 | 12.0 | 0 | 825.0 | 67 | 372915 | 100, 100, 100 |
| production /credits | 100 | 100 | 100 | 100 | 844.0 | 1123.0 | 13 | 0 | 844.0 | 62 | 377520 | 99, 100, 100 |
| production /offline | 99 | 100 | 100 | 100 | 835.0 | 1797.0 | 16.0 | 0 | 2109.0 | 77 | 410976 | 99, 100, 99 |
| production /share/12 | 99 | 100 | 100 | 100 | 851.0 | 1803.0 | 22 | 0 | 2128.0 | 58 | 413580 | 99, 99, 99 |
| production /accessibility | 100 | 100 | 100 | 100 | 811.0 | 1103.0 | 13.0 | 0 | 811.0 | 58 | 372629 | 99, 100, 100 |
| production /verify | 99 | 100 | 100 | 100 | 973.0 | 2023.0 | 11 | 0 | 2129.0 | 69 | 411222 | 99, 99, 99 |
| production /city?creek=strawberry-creek | 99 | 100 | 100 | 100 | 839.0 | 2028.0 | 22.0 | 0 | 839.0 | 56 | 413230 | 97, 99, 99 |
| production /walk | 99 | 100 | 100 | 100 | 841.0 | 2000.0 | 23 | 0 | 2173.0 | 99 | 993076 | 99, 99, 99 |
| production /walk/v02 | 98 | 100 | 100 | 100 | 833.0 | 2441.0 | 6.0 | 0 | 2145.0 | 73 | 696795 | 98, 98, 100 |

Not measured, because they are not deployed there:


Lighthouse warnings:

- The page loaded too slowly to finish within the time limit. Results may be incomplete.
