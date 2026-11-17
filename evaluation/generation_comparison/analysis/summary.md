# Analysis summary (2026-11-17T17:39:32+00:00)

git commit `852e104ff215a6ff7f3bb241af99b6ac7e93ffed` (dirty=False); CPU Intel64 Family 6 Model 154 Stepping 4, GenuineIntel, 10 physical / 12 logical cores, RAM 31.69 GB, on battery=False
- fast: `Llama-3.2-1B-Instruct.Q4_K_M.gguf` sha256 match=True threads=11 temp=0.6
- staged: `Qwen2.5-3B-Instruct.Q4_K_M.gguf` sha256 match=True threads=11 temp=0.6

## Every run (failures included)

| run | cond | status | e2e s | load s | infer s | python s | out tok | tok/s | peak RAM MB | source | substantive DSL | schema ok | validator issues | clue reaches culprit deed | compiler proof (1B only) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e1_fast_cold__g0__00_s1 | cold | ok | 9.9592 | 1.3338 | 8.5955 | 0.0299 | 277 | 32.226 | 1472.4 | model | True | True | 0 | True | True |
| e1_fast_cold__g1__00_s2 | cold | ok | 10.7517 | 0.9904 | 9.7281 | 0.0332 | 292 | 30.016 | 1471.7 | model | True | True | 0 | True | True |
| e1_fast_cold__g2__00_s3 | cold | ok | 9.5666 | 0.9602 | 8.5703 | 0.0361 | 259 | 30.221 | 1471.8 | model | True | True | 0 | True | True |
| e1_fast_cold__g3__00_s4 | cold | ok | 9.7663 | 0.9466 | 8.7916 | 0.028 | 270 | 30.711 | 1472.2 | model | True | True | 0 | True | True |
| e1_fast_cold__g4__00_s5 | cold | ok | 8.9696 | 0.9929 | 7.95 | 0.0268 | 243 | 30.566 | 1472.2 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__00_s1000_warmup | warmup | ok | 9.8243 | 0.9752 | 8.8144 | 0.0346 | 271 | 30.745 | 1472.0 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__01_s1 | warm | ok | 7.8409 | 0.0 | 7.818 | 0.0228 | 255 | 32.617 | 1473.8 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__02_s2 | warm | ok | 9.2307 | 0.0 | 9.2014 | 0.0293 | 292 | 31.734 | 1475.4 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__03_s3 | warm | ok | 9.5614 | 0.0 | 9.5338 | 0.0276 | 299 | 31.362 | 1476.9 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__04_s4 | warm | ok | 8.4525 | 0.0 | 8.4298 | 0.0226 | 270 | 32.029 | 1478.3 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__05_s5 | warm | ok | 7.647 | 0.0 | 7.6182 | 0.0288 | 243 | 31.897 | 1478.4 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__06_s6 | warm | ok | 9.462 | 0.0 | 9.431 | 0.031 | 297 | 31.492 | 1479.9 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__07_s7 | warm | ok | 8.5663 | 0.0 | 8.541 | 0.0254 | 275 | 32.198 | 1481.3 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__08_s8 | warm | ok | 8.1696 | 0.0 | 8.1429 | 0.0267 | 262 | 32.175 | 1481.4 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__09_s9 | warm | ok | 8.3586 | 0.0 | 8.3372 | 0.0213 | 266 | 31.905 | 1482.9 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__10_s10 | warm | ok | 8.4411 | 0.0 | 8.4109 | 0.0302 | 269 | 31.982 | 1484.3 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__11_s11 | warm | ok | 8.8553 | 0.0 | 8.8343 | 0.021 | 271 | 30.676 | 1484.3 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__12_s12 | warm | ok | 9.5392 | 0.0 | 9.5187 | 0.0205 | 292 | 30.677 | 1485.8 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__13_s13 | warm | ok | 8.8544 | 0.0 | 8.8318 | 0.0227 | 273 | 30.911 | 1487.3 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__14_s14 | warm | ok | 9.749 | 0.0 | 9.7291 | 0.0199 | 290 | 29.807 | 1474.1 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__15_s15 | warm | ok | 8.9381 | 0.0 | 8.914 | 0.0242 | 279 | 31.299 | 1475.8 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__16_s16 | warm | ok | 9.7523 | 0.0 | 9.7296 | 0.0227 | 299 | 30.731 | 1477.8 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__17_s17 | warm | ok | 9.0966 | 0.0 | 9.0728 | 0.0238 | 287 | 31.633 | 1477.8 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__18_s18 | warm | ok | 8.9114 | 0.0 | 8.8906 | 0.0208 | 282 | 31.719 | 1479.2 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__19_s19 | warm | ok | 9.5498 | 0.0 | 9.5265 | 0.0233 | 294 | 30.861 | 1480.7 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__20_s20 | warm | ok | 8.899 | 0.0 | 8.8714 | 0.0277 | 285 | 32.126 | 1480.7 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__21_s21 | warm | ok | 8.6097 | 0.0 | 8.5849 | 0.0248 | 270 | 31.451 | 1482.2 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__22_s22 | warm | ok | 8.9271 | 0.0 | 8.9052 | 0.0219 | 272 | 30.544 | 1483.6 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__23_s23 | warm | ok | 9.5538 | 0.0 | 9.5273 | 0.0264 | 293 | 30.754 | 1483.6 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__24_s24 | warm | ok | 8.9258 | 0.0 | 8.9008 | 0.025 | 276 | 31.008 | 1485.1 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__25_s25 | warm | ok | 9.7243 | 0.0 | 9.7008 | 0.0235 | 294 | 30.307 | 1486.6 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__26_s26 | warm | ok | 9.094 | 0.0 | 9.0684 | 0.0256 | 271 | 29.884 | 1486.6 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__27_s27 | warm | ok | 10.2036 | 0.0 | 10.177 | 0.0266 | 291 | 28.594 | 1488.0 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__28_s28 | warm | ok | 9.7493 | 0.0 | 9.7227 | 0.0266 | 290 | 29.827 | 1489.5 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__29_s29 | warm | ok | 9.2132 | 0.0 | 9.1877 | 0.0256 | 269 | 29.278 | 1489.5 | model | True | True | 0 | True | True |
| e1_fast_warm__g0__30_s30 | warm | ok | 9.0718 | 0.0 | 9.0436 | 0.0283 | 270 | 29.855 | 1491.0 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__00_s1000_warmup | warmup | ok | 9.725 | 0.9036 | 8.7929 | 0.0285 | 271 | 30.82 | 1472.1 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__01_s1 | warm | ok | 8.0354 | 0.0 | 8.0094 | 0.026 | 255 | 31.838 | 1473.9 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__02_s2 | warm | ok | 9.2723 | 0.0 | 9.2498 | 0.0225 | 292 | 31.568 | 1475.4 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__03_s3 | warm | ok | 9.5989 | 0.0 | 9.5765 | 0.0224 | 299 | 31.222 | 1476.9 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__04_s1 | warm | ok | 7.9513 | 0.0 | 7.9275 | 0.0238 | 255 | 32.167 | 1478.4 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__05_s2 | warm | ok | 9.361 | 0.0 | 9.336 | 0.025 | 292 | 31.277 | 1478.4 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__06_s3 | warm | ok | 9.9485 | 0.0 | 9.9224 | 0.0261 | 299 | 30.134 | 1479.8 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__07_s1 | warm | ok | 8.0391 | 0.0 | 8.0147 | 0.0244 | 255 | 31.817 | 1481.3 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__08_s2 | warm | ok | 9.1644 | 0.0 | 9.1396 | 0.0248 | 292 | 31.949 | 1481.5 | model | True | True | 0 | True | True |
| e3_fast_repeat__g0__09_s3 | warm | ok | 9.4124 | 0.0 | 9.3878 | 0.0246 | 299 | 31.85 | 1482.9 | model | True | True | 0 | True | True |
| e2_staged__g0__00_s1 | cold | ok | 692.1631 | 3.4126 | 688.6695 | 0.0811 | 3656 | 5.309 | 3547.8 | staged | – | True | 0 | True | – |
| e2_staged__g1__00_s2 | cold | ok | 623.1616 | 2.6024 | 620.4923 | 0.0669 | 3245 | 5.23 | 3544.0 | staged | – | True | 0 | True | – |
| e2_staged__g2__00_s3 | cold | failed | – | 2.7469 | 628.0414 | – | 3063 | 4.877 | 3540.2 | – | – | – | – | – | – |
| e3_staged_repeat__g0__00_s1 | cold | ok | 1363.3039 | 1.5091 | 1361.7258 | 0.069 | 3656 | 2.685 | 3547.0 | staged | – | True | 0 | True | – |

## Outcome counts per step (nothing excluded)

- **e1_fast_cold**: 5 records -> {'ok': 5}
- **e1_fast_warm**: 31 records -> {'ok': 31}
- **e2_staged**: 3 records -> {'ok': 2, 'failed': 1}
- **e3_fast_repeat**: 10 records -> {'ok': 10}
- **e3_staged_repeat**: 1 records -> {'ok': 1}

## Descriptive statistics (successful, non-warm-up runs)

SD is shown only for n ≥ 2; treat any statistic with n < 5 as a case study, not an estimate.

| route | condition | step | metric | n | mean | median | sd | min | max |
|---|---|---|---|---|---|---|---|---|---|
| fast | cold | e1_fast_cold | e2e_s | 5 | 9.803 | 9.766 | 0.647 | 8.97 | 10.752 |
| fast | cold | e1_fast_cold | load_s | 5 | 1.045 | 0.99 | 0.163 | 0.947 | 1.334 |
| fast | cold | e1_fast_cold | infer_s | 5 | 8.727 | 8.595 | 0.643 | 7.95 | 9.728 |
| fast | cold | e1_fast_cold | python_s | 5 | 0.031 | 0.03 | 0.004 | 0.027 | 0.036 |
| fast | cold | e1_fast_cold | output_tokens | 5 | 268.2 | 270 | 18.485 | 243 | 292 |
| fast | cold | e1_fast_cold | tok_per_s | 5 | 30.748 | 30.566 | 0.871 | 30.016 | 32.226 |
| fast | cold | e1_fast_cold | rss_peak_mb | 5 | 1472.06 | 1472.2 | 0.297 | 1471.7 | 1472.4 |
| fast | warm | e1_fast_warm | e2e_s | 30 | 9.032 | 9.005 | 0.601 | 7.647 | 10.204 |
| fast | warm | e1_fast_warm | load_s | 30 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| fast | warm | e1_fast_warm | infer_s | 30 | 9.007 | 8.979 | 0.601 | 7.618 | 10.177 |
| fast | warm | e1_fast_warm | python_s | 30 | 0.025 | 0.025 | 0.003 | 0.02 | 0.031 |
| fast | warm | e1_fast_warm | output_tokens | 30 | 279.2 | 277.5 | 13.912 | 243 | 299 |
| fast | warm | e1_fast_warm | tok_per_s | 30 | 31.044 | 31.154 | 0.975 | 28.594 | 32.617 |
| fast | warm | e1_fast_warm | rss_peak_mb | 30 | 1482.06 | 1481.8 | 4.758 | 1473.8 | 1491.0 |
| fast | warm | e3_fast_repeat | e2e_s | 9 | 8.976 | 9.272 | 0.759 | 7.951 | 9.948 |
| fast | warm | e3_fast_repeat | load_s | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| fast | warm | e3_fast_repeat | infer_s | 9 | 8.952 | 9.25 | 0.759 | 7.928 | 9.922 |
| fast | warm | e3_fast_repeat | python_s | 9 | 0.024 | 0.025 | 0.001 | 0.022 | 0.026 |
| fast | warm | e3_fast_repeat | output_tokens | 9 | 282.0 | 292 | 20.476 | 255 | 299 |
| fast | warm | e3_fast_repeat | tok_per_s | 9 | 31.536 | 31.817 | 0.609 | 30.134 | 32.167 |
| fast | warm | e3_fast_repeat | rss_peak_mb | 9 | 1478.722 | 1478.4 | 2.975 | 1473.9 | 1482.9 |
| staged | cold | e2_staged | e2e_s | 2 | 657.662 | 657.662 | 48.791 | 623.162 | 692.163 |
| staged | cold | e2_staged | load_s | 2 | 3.007 | 3.007 | 0.573 | 2.602 | 3.413 |
| staged | cold | e2_staged | infer_s | 2 | 654.581 | 654.581 | 48.209 | 620.492 | 688.669 |
| staged | cold | e2_staged | python_s | 2 | 0.074 | 0.074 | 0.01 | 0.067 | 0.081 |
| staged | cold | e2_staged | output_tokens | 2 | 3450.5 | 3450.5 | 290.621 | 3245 | 3656 |
| staged | cold | e2_staged | tok_per_s | 2 | 5.27 | 5.27 | 0.056 | 5.23 | 5.309 |
| staged | cold | e2_staged | rss_peak_mb | 2 | 3545.9 | 3545.9 | 2.687 | 3544.0 | 3547.8 |
| staged | cold | e3_staged_repeat | e2e_s | 1 | 1363.304 | 1363.304 | – | 1363.304 | 1363.304 |
| staged | cold | e3_staged_repeat | load_s | 1 | 1.509 | 1.509 | – | 1.509 | 1.509 |
| staged | cold | e3_staged_repeat | infer_s | 1 | 1361.726 | 1361.726 | – | 1361.726 | 1361.726 |
| staged | cold | e3_staged_repeat | python_s | 1 | 0.069 | 0.069 | – | 0.069 | 0.069 |
| staged | cold | e3_staged_repeat | output_tokens | 1 | 3656.0 | 3656 | – | 3656 | 3656 |
| staged | cold | e3_staged_repeat | tok_per_s | 1 | 2.685 | 2.685 | – | 2.685 | 2.685 |
| staged | cold | e3_staged_repeat | rss_peak_mb | 1 | 3547.0 | 3547.0 | – | 3547.0 | 3547.0 |

## 1B blueprint provenance

- `Blueprint: model`: 44/44 runs
- model blueprint contained header + premise + cast + crime + ≥1 timeline + ≥1 clue line: 44/44
- (A run can say `model` while most content is compiler defaults; the second line checks that.)

## Repeatability (same seed, same settings)

| route | seed | runs | distinct bundles | distinct raw model texts | e2e range s |
|---|---|---|---|---|---|
| fast | 1 | 5 | 2 | 2 | (7.84, 9.96) |
| fast | 2 | 5 | 1 | 1 | (9.16, 10.75) |
| fast | 3 | 5 | 2 | 2 | (9.41, 9.95) |
| fast | 4 | 2 | 2 | 2 | (8.45, 9.77) |
| fast | 5 | 2 | 2 | 2 | (7.65, 8.97) |
| staged | 1 | 2 | 1 | see raw/ | (692.16, 1363.3) |

## Does the seed change the mystery? (e1_fast_warm)

- 31 distinct bundles from 31 seeds
- 5 distinct titles, 15 distinct culprit names
