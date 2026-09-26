# Lighthouse

Measured 2026-09-26T02:49:48Z by `uv run python scripts/harden_lighthouse.py`, Lighthouse 13.5.0 in headless Chrome on this Mac (8 CPUs). Default mobile run, which is the throttled 4G profile: a mid-range phone screen, simulated 150 ms round trip at 1.6 Mbps down, CPU slowed four times. Three runs per page; the table shows the run with the median performance score, and the last column shows all three. Full reports stay outside the repo.

| Page | Perf | A11y | Best practices | SEO | FCP ms | LCP ms | TBT ms | CLS | SI ms | TTFB ms | Bytes | Perf, all runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| production / | 96 | 100 | 100 | 100 | 847.0 | 2468.0 | 20.0 | 0 | 3560.0 | 56 | 377716 | 96, 96, 95 |
| production /t | 99 | 100 | 100 | 100 | 857.0 | 2026.0 | 70 | 0 | 2426.0 | 94 | 407522 | 99, 99, 95 |
| production /demo | 99 | 100 | 100 | 100 | 820.0 | 2007.0 | 56 | 0 | 2126.0 | 73 | 413004 | 100, 99, 99 |
| production /t2 | 99 | 100 | 100 | 100 | 821.0 | 2001.0 | 23 | 0 | 2168.0 | 102 | 409009 | 99, 99, 99 |
| production /t2/demo | 100 | 100 | 100 | 100 | 819.0 | 1257.0 | 22.0 | 0 | 819.0 | 57 | 414641 | 100, 100, 100 |
| production /judges | 99 | 100 | 100 | 100 | 1414.0 | 1802.0 | 38 | 0 | 2529.0 | 72 | 401166 | 96, 99, 100 |
| production /check | 99 | 100 | 100 | 100 | 833.0 | 2021.0 | 60 | 0 | 2097.0 | 66 | 407823 | 99, 99, 100 |
| production /spot | 99 | 100 | 100 | 100 | 827.0 | 2011.0 | 47 | 0 | 2131.0 | 82 | 417141 | 99, 99, 99 |
| production /quick | 99 | 100 | 100 | 100 | 848.0 | 2019.0 | 60 | 0 | 2161.0 | 95 | 407094 | 99, 99, 99 |
| production /two | 100 | 100 | 100 | 100 | 833.0 | 1423.0 | 16.0 | 0 | 908.0 | 58 | 403335 | 100, 100, 100 |
| production /poster | 98 | 100 | 100 | 100 | 838.0 | 2416.0 | 23 | 0 | 2174.0 | 43 | 369424 | 98, 96, 98 |
| production /how-we-know | 99 | 100 | 100 | 100 | 1113.0 | 1958.0 | 49 | 0 | 2338.0 | 72 | 473013 | 98, 99, 99 |
| production /about | 99 | 100 | 100 | 100 | 826.0 | 1812.0 | 52 | 0 | 2239.0 | 129 | 373899 | 99, 100, 99 |
| production /privacy | 99 | 100 | 100 | 100 | 822.0 | 1811.0 | 55 | 0 | 2142.0 | 82 | 369024 | 100, 99, 99 |
| production /credits | 100 | 100 | 100 | 100 | 836.0 | 1414.0 | 16.0 | 0 | 836.0 | 52 | 377335 | 100, 100, 99 |
| production /offline | 99 | 100 | 100 | 100 | 840.0 | 1856.0 | 81 | 0 | 2160.0 | 73 | 373586 | 99, 99, 99 |
| production /share/12 | 100 | 100 | 100 | 100 | 838.0 | 1792.0 | 42 | 0 | 2162.0 | 54 | 376058 | 99, 100, 100 |
| production /accessibility | 100 | 100 | 100 | 100 | 821.0 | 1105.0 | 21.0 | 0 | 821.0 | 56 | 371958 | 100, 100, 97 |
| production /verify | 99 | 100 | 100 | 100 | 963.0 | 2013.0 | 63 | 0 | 2170.0 | 81 | 412951 | 100, 99, 99 |
| production /city?creek=strawberry-creek | 99 | 100 | 100 | 100 | 831.0 | 2013.0 | 81 | 0 | 2094.0 | 58 | 419347 | 99, 99, 99 |
| production /walk | 99 | 100 | 100 | 100 | 823.0 | 2161.0 | 34 | 0 | 2188.0 | 66 | 976613 | 97, 99, 99 |
| production /walk/v02 | 93 | 100 | 100 | 100 | 849.0 | 3059.0 | 33 | 0 | 3550.0 | 56 | 495091 | 92, 97, 93 |

Not measured, because they are not deployed there:


Lighthouse warnings:

- The page loaded too slowly to finish within the time limit. Results may be incomplete.
