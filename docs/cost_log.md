# Live model cost log

Generated from `runtime/costs/ledger.jsonl` by `scripts/demo/live_run.py`. Costs use each call's reported token usage and
the published rates held in `config/models.yaml` (price date shown per model). Calls served by a fallback model are listed as unpriced.

## Running totals by model

| Model | Route | Calls | Input tokens | Output tokens | Cost (USD) | Unpriced calls |
|---|---|---|---|---|---|---|
| claude-fable-5-2 | direct | 103 | 6,534,245 | 809,581 | 84.6572 | 0 |

## Calls

| When (UTC) | Model | Case | Section | Purpose | Input | Output | Cost (USD) | Seconds |
|---|---|---|---|---|---|---|---|---|
| 2026-11-11T17:10:45 | claude-fable-5-2 | demo-new-001 | 2 | draft | 63,356 | 4,112 | 0.671328 | 36.0 |
| 2026-11-11T17:12:00 | claude-fable-5-2 | demo-new-001 | 1 | draft | 67,450 | 2,130 | 0.624800 | 20.8 |
| 2026-11-11T17:12:21 | claude-fable-5-2 | demo-new-001 | 2 | draft | 63,546 | 2,922 | 0.625248 | 26.5 |
| 2026-11-11T17:12:48 | claude-fable-5-2 | demo-new-001 | 3 | draft | 64,554 | 1,445 | 0.574232 | 13.9 |
| 2026-11-11T17:13:02 | claude-fable-5-2 | demo-new-001 | 4 | draft | 66,597 | 26,369 | 1.587536 | 214.1 |
| 2026-11-11T17:16:37 | claude-fable-5-2 | demo-new-001 | 5 | draft | 68,965 | 4,780 | 0.742920 | 42.5 |
| 2026-11-11T17:17:20 | claude-fable-5-2 | demo-new-001 | 6 | draft | 70,508 | 8,498 | 0.903984 | 67.7 |
| 2026-11-11T17:18:28 | claude-fable-5-2 | demo-new-001 | 7 | draft | 65,889 | 4,409 | 0.703472 | 40.8 |
| 2026-11-11T17:19:09 | claude-fable-5-2 | demo-new-001 | 8 | draft | 68,200 | 5,598 | 0.769520 | 49.7 |
| 2026-11-11T17:19:59 | claude-fable-5-2 | demo-new-001 | 10 | draft | 61,810 | 32,000 | 1.774480 | 279.7 |
| 2026-11-11T17:25:28 | claude-fable-5-2 | demo-new-001 | 10 | draft | 60,369 | 27,715 | 1.591552 | 228.7 |
| 2026-11-11T17:29:17 | claude-fable-5-2 | demo-new-001 | 10 | draft | 62,246 | 14,389 | 1.073528 | 125.6 |
| 2026-11-11T17:31:23 | claude-fable-5-2 | demo-new-001 | 9 | draft | 63,436 | 5,157 | 0.713768 | 48.7 |
| 2026-11-11T17:32:12 | claude-fable-5-2 | demo-new-001 | 11 | draft | 84,589 | 6,768 | 0.947432 | 62.0 |
| 2026-11-11T17:33:15 | claude-fable-5-2 | demo-new-001 | 12 | draft | 63,602 | 2,334 | 0.602176 | 21.7 |
| 2026-11-11T17:33:37 | claude-fable-5-2 | demo-new-001 | 14 | draft | 92,862 | 7,066 | 1.025536 | 60.4 |
| 2026-11-11T17:35:04 | claude-fable-5-2 | demo-new-001 | 4 | draft | 66,645 | 23,206 | 1.461400 | 188.2 |
| 2026-11-11T17:38:13 | claude-fable-5-2 | demo-new-001 | 5 | draft | 69,013 | 4,775 | 0.743104 | 40.5 |
| 2026-11-11T17:38:54 | claude-fable-5-2 | demo-new-001 | 8 | draft | 68,248 | 5,216 | 0.754624 | 45.4 |
| 2026-11-11T17:43:31 | claude-fable-5-2 | demo-new-001 | 1 | draft | 81,686 | 3,417 | 0.790168 | 28.0 |
| 2026-11-11T17:43:59 | claude-fable-5-2 | demo-new-001 | 2 | draft | 80,424 | 3,572 | 0.786272 | 30.7 |
| 2026-11-11T17:44:31 | claude-fable-5-2 | demo-new-001 | 3 | draft | 81,337 | 1,554 | 0.712856 | 17.4 |
| 2026-11-11T17:44:48 | claude-fable-5-2 | demo-new-001 | 4 | draft | 78,895 | 21,384 | 1.486520 | 173.7 |
| 2026-11-11T17:47:42 | claude-fable-5-2 | demo-new-001 | 4 | draft | 77,853 | 3,850 | 0.776824 | 34.6 |
| 2026-11-11T17:48:17 | claude-fable-5-2 | demo-new-001 | 5 | draft | 84,413 | 5,543 | 0.897024 | 51.4 |
| 2026-11-11T17:49:09 | claude-fable-5-2 | demo-new-001 | 6 | draft | 86,430 | 7,812 | 1.003920 | 65.6 |
| 2026-11-11T17:50:15 | claude-fable-5-2 | demo-new-001 | 7 | draft | 82,979 | 3,770 | 0.814632 | 34.9 |
| 2026-11-11T17:50:51 | claude-fable-5-2 | demo-new-001 | 8 | draft | 84,668 | 5,129 | 0.882504 | 46.9 |
| 2026-11-11T17:51:38 | claude-fable-5-2 | demo-new-001 | 10 | draft | 73,042 | 25,031 | 1.585576 | 210.9 |
| 2026-11-11T17:55:09 | claude-fable-5-2 | demo-new-001 | 10 | draft | 79,167 | 14,566 | 1.215976 | 128.6 |
| 2026-11-11T17:57:18 | claude-fable-5-2 | demo-new-001 | 10 | draft | 79,412 | 4,719 | 0.824056 | 44.9 |
| 2026-11-11T17:58:03 | claude-fable-5-2 | demo-new-001 | 9 | draft | 79,124 | 4,740 | 0.822592 | 42.9 |
| 2026-11-11T17:58:47 | claude-fable-5-2 | demo-new-001 | 11 | draft | 99,719 | 9,110 | 1.162152 | 77.9 |
| 2026-11-11T18:00:05 | claude-fable-5-2 | demo-new-001 | 12 | draft | 78,010 | 2,673 | 0.731000 | 26.5 |
| 2026-11-11T18:00:32 | claude-fable-5-2 | demo-new-001 | 14 | draft | 107,531 | 6,366 | 1.114888 | 55.5 |
| 2026-11-11T18:09:14 | claude-fable-5-2 | demo-new-001 | 4 | draft | 60,776 | 16,950 | 1.164208 | 139.6 |
| 2026-11-11T18:11:33 | claude-fable-5-2 | demo-new-001 | 4 | draft | 67,202 | 4,024 | 0.698576 | 37.5 |
| 2026-11-11T18:12:12 | claude-fable-5-2 | demo-new-001 | 10 | draft | 59,443 | 27,120 | 1.560344 | 222.7 |
| 2026-11-11T18:15:54 | claude-fable-5-2 | demo-new-001 | 10 | draft | 58,900 | 14,046 | 1.033040 | 121.4 |
| 2026-11-11T18:17:56 | claude-fable-5-2 | demo-new-001 | 10 | draft | 73,769 | 2,961 | 0.708592 | 32.3 |
| 2026-11-11T18:18:29 | claude-fable-5-2 | demo-new-001 | 11 | draft | 95,132 | 7,917 | 1.077736 | 69.0 |
| 2026-11-11T18:19:38 | claude-fable-5-2 | demo-new-001 | 14 | draft | 95,565 | 5,970 | 1.003320 | 52.7 |
| 2026-11-11T18:22:10 | claude-fable-5-2 | demo-new-001 | 1 | draft | 74,952 | 2,354 | 0.693776 | 23.0 |
| 2026-11-11T18:22:33 | claude-fable-5-2 | demo-new-001 | 2 | draft | 69,245 | 3,916 | 0.710600 | 38.0 |
| 2026-11-11T18:23:12 | claude-fable-5-2 | demo-new-001 | 3 | draft | 76,371 | 1,665 | 0.677568 | 15.4 |
| 2026-11-11T18:23:28 | claude-fable-5-2 | demo-new-001 | 4 | draft | 76,031 | 17,836 | 1.321688 | 151.9 |
| 2026-11-11T18:26:00 | claude-fable-5-2 | demo-new-001 | 4 | draft | 67,214 | 4,317 | 0.710392 | 41.0 |
| 2026-11-11T18:26:42 | claude-fable-5-2 | demo-new-001 | 5 | draft | 52,980 | 5,485 | 0.643240 | 45.8 |
| 2026-11-11T18:27:28 | claude-fable-5-2 | demo-new-001 | 6 | draft | 66,980 | 8,533 | 0.877160 | 69.1 |
| 2026-11-11T18:28:37 | claude-fable-5-2 | demo-new-001 | 7 | draft | 72,329 | 3,965 | 0.737232 | 32.9 |
| 2026-11-11T18:29:11 | claude-fable-5-2 | demo-new-001 | 8 | draft | 68,125 | 5,865 | 0.779600 | 51.0 |
| 2026-11-11T18:30:02 | claude-fable-5-2 | demo-new-001 | 10 | draft | 59,455 | 25,562 | 1.498120 | 210.7 |
| 2026-11-11T18:33:33 | claude-fable-5-2 | demo-new-001 | 10 | draft | 58,912 | 11,924 | 0.948256 | 103.7 |
| 2026-11-11T18:35:17 | claude-fable-5-2 | demo-new-001 | 10 | draft | 73,781 | 3,756 | 0.740488 | 34.5 |
| 2026-11-11T18:35:52 | claude-fable-5-2 | demo-new-001 | 9 | draft | 65,772 | 5,437 | 0.743656 | 51.3 |
| 2026-11-11T18:36:44 | claude-fable-5-2 | demo-new-001 | 11 | draft | 95,673 | 7,440 | 1.062984 | 67.8 |
| 2026-11-11T18:37:52 | claude-fable-5-2 | demo-new-001 | 12 | draft | 46,036 | 2,254 | 0.458448 | 22.5 |
| 2026-11-11T18:38:15 | claude-fable-5-2 | demo-new-001 | 14 | draft | 96,044 | 5,789 | 0.999912 | 51.1 |
| 2026-11-12T00:15:11 | claude-fable-5-2 | demo-new-001 | 12 | draft | 46,556 | 2,366 | 0.467088 | 21.4 |
| 2026-11-12T00:15:33 | claude-fable-5-2 | demo-new-001 | 14 | draft | 96,402 | 5,538 | 0.992736 | 45.4 |
| 2026-11-12T00:27:57 | claude-fable-5-2 | demo-new-001 | 12 | draft | 46,556 | 2,521 | 0.473288 | 22.5 |
| 2026-11-12T00:37:28 | claude-fable-5-2 | demo-new-001 | 8 | draft | 68,466 | 6,045 | 0.789528 | 52.6 |
| 2026-11-12T00:38:50 | claude-fable-5-2 | demo-new-001 | 14 | draft | 96,517 | 4,915 | 0.968736 | 43.1 |
| 2026-11-12T00:41:30 | claude-fable-5-2 | demo-new-001 | 10 | draft | 59,796 | 21,609 | 1.342728 | 173.5 |
| 2026-11-12T00:44:23 | claude-fable-5-2 | demo-new-001 | 10 | draft | 59,253 | 16,190 | 1.121624 | 138.2 |
| 2026-11-12T00:46:42 | claude-fable-5-2 | demo-new-001 | 10 | draft | 74,122 | 4,806 | 0.785216 | 43.9 |
| 2026-11-12T00:47:26 | claude-fable-5-2 | demo-new-001 | 11 | draft | 96,148 | 9,958 | 1.167504 | 80.2 |
| 2026-11-12T00:48:47 | claude-fable-5-2 | demo-new-001 | 14 | draft | 96,534 | 5,169 | 0.979032 | 43.6 |
| 2026-11-12T01:38:55 | claude-fable-5-2 | demo-new-001 | 12 | draft | 46,556 | 2,265 | 0.463048 | 20.5 |
| 2026-11-12T16:58:32 | claude-fable-5-2 | demo-new-001 | 5 | sense_check | 3,607 | 379 | 0.044016 | 4.1 |
| 2026-11-12T16:59:09 | claude-fable-5-2 | demo-new-001 | 2 | sense_check | 3,225 | 804 | 0.057960 | 8.6 |
| 2026-11-12T16:59:17 | claude-fable-5-2 | demo-new-001 | 3 | sense_check | 3,078 | 453 | 0.042744 | 5.5 |
| 2026-11-12T16:59:23 | claude-fable-5-2 | demo-new-001 | 4 | sense_check | 5,478 | 11,345 | 0.497624 | 114.5 |
| 2026-11-12T17:01:17 | claude-fable-5-2 | demo-new-001 | 5 | sense_check | 3,399 | 566 | 0.049832 | 7.2 |
| 2026-11-12T17:01:25 | claude-fable-5-2 | demo-new-001 | 6 | sense_check | 4,500 | 1,134 | 0.081360 | 10.6 |
| 2026-11-12T17:01:35 | claude-fable-5-2 | demo-new-001 | 7 | sense_check | 4,113 | 592 | 0.056584 | 7.1 |
| 2026-11-12T17:01:42 | claude-fable-5-2 | demo-new-001 | 8 | sense_check | 3,933 | 951 | 0.069504 | 12.3 |
| 2026-11-12T17:01:55 | claude-fable-5-2 | demo-new-001 | 10 | sense_check | 6,975 | 11,018 | 0.496520 | 108.5 |
| 2026-11-12T17:03:43 | claude-fable-5-2 | demo-new-001 | 11 | sense_check | 5,526 | 2,683 | 0.151528 | 24.7 |
| 2026-11-12T17:04:08 | claude-fable-5-2 | demo-new-001 | 12 | sense_check | 3,168 | 848 | 0.059264 | 8.4 |
| 2026-11-12T17:04:16 | claude-fable-5-2 | demo-new-001 | 14 | sense_check | 3,578 | 902 | 0.064704 | 9.0 |
| 2026-11-12T17:04:51 | claude-fable-5-2 | demo-new-001 | 4 | sense_check | 5,501 | 5,548 | 0.265928 | 55.1 |
| 2026-11-12T17:31:11 | claude-fable-5-2 | demo-new-001 | 5 | sense_check | 3,630 | 477 | 0.048120 | 5.0 |
| 2026-11-13T06:16:20 | claude-fable-5-2 | demo-new-001 | 8 | draft | 69,072 | 6,875 | 0.827576 | 59.2 |
| 2026-11-13T06:17:23 | claude-fable-5-2 | demo-new-001 | 1 | draft | 75,899 | 3,792 | 0.758872 | 31.2 |
| 2026-11-13T06:17:57 | claude-fable-5-2 | demo-new-001 | 2 | draft | 70,192 | 4,087 | 0.725016 | 38.1 |
| 2026-11-13T06:18:38 | claude-fable-5-2 | demo-new-001 | 3 | draft | 77,318 | 1,527 | 0.679624 | 15.1 |
| 2026-11-13T06:18:56 | claude-fable-5-2 | demo-new-001 | 4 | draft | 76,978 | 19,622 | 1.400704 | 162.2 |
| 2026-11-13T06:21:38 | claude-fable-5-2 | demo-new-001 | 4 | draft | 68,161 | 4,826 | 0.738328 | 42.6 |
| 2026-11-13T06:22:25 | claude-fable-5-2 | demo-new-001 | 5 | draft | 53,927 | 5,788 | 0.662936 | 48.7 |
| 2026-11-13T06:23:17 | claude-fable-5-2 | demo-new-001 | 6 | draft | 67,927 | 8,582 | 0.886696 | 70.8 |
| 2026-11-13T06:24:31 | claude-fable-5-2 | demo-new-001 | 7 | draft | 73,276 | 4,436 | 0.763648 | 36.9 |
| 2026-11-13T06:25:11 | claude-fable-5-2 | demo-new-001 | 10 | draft | 60,402 | 25,072 | 1.486096 | 205.5 |
| 2026-11-13T06:28:37 | claude-fable-5-2 | demo-new-001 | 10 | draft | 59,859 | 15,834 | 1.112232 | 139.7 |
| 2026-11-13T06:30:56 | claude-fable-5-2 | demo-new-001 | 10 | draft | 74,728 | 4,102 | 0.761904 | 38.3 |
| 2026-11-13T06:31:39 | claude-fable-5-2 | demo-new-001 | 9 | draft | 66,719 | 4,853 | 0.727872 | 43.7 |
| 2026-11-13T06:32:26 | claude-fable-5-2 | demo-new-001 | 11 | draft | 97,586 | 10,788 | 1.212208 | 87.2 |
| 2026-11-13T06:33:56 | claude-fable-5-2 | demo-new-001 | 14 | draft | 98,362 | 5,936 | 1.024336 | 49.0 |
| 2026-11-13T06:36:56 | claude-fable-5-2 | demo-new-001 | 8 | draft | 69,072 | 6,221 | 0.801416 | 52.3 |
| 2026-11-13T06:37:51 | claude-fable-5-2 | demo-new-001 | 1 | draft | 75,899 | 3,832 | 0.760472 | 32.8 |
| 2026-11-13T06:38:27 | claude-fable-5-2 | demo-new-001 | 10 | draft | 60,402 | 25,076 | 1.486256 | 205.3 |
| 2026-11-13T06:41:52 | claude-fable-5-2 | demo-new-001 | 10 | draft | 59,859 | 16,703 | 1.146992 | 149.9 |
| 2026-11-13T06:44:22 | claude-fable-5-2 | demo-new-001 | 10 | draft | 74,728 | 5,336 | 0.811264 | 47.2 |
