# ArXiv.org RSS Scrubber

```
usage: python -m arxivrss [-h] -o DIR SUBJ [SUBJ ...]

positional arguments:
  SUBJ

optional arguments:
  -h, --help  show this help message and exit
  -o DIR      output directory
```

```bash
$ python -m arxivrss -o output cs.CV cs.CL cs.SI nucl-th stat.AP cs.LG stat.ML
2020-05-17 20:09:49,262 [cs.CV] Collecting subject
2020-05-17 20:09:51,001 [cs.CV] Created feed <Feed [cs.CV] with 63 articles>
2020-05-17 20:09:51,001 [cs.CL] Collecting subject
2020-05-17 20:09:52,399 [cs.CL] Created feed <Feed [cs.CL] with 62 articles>
2020-05-17 20:09:52,400 [cs.SI] Collecting subject
2020-05-17 20:09:53,683 [cs.SI] Created feed <Feed [cs.SI] with 22 articles>
2020-05-17 20:09:53,683 [nucl-th] Collecting subject
2020-05-17 20:09:54,237 [nucl-th] Created feed <Feed [nucl-th] with 16 articles>
2020-05-17 20:09:54,238 [stat.AP] Collecting subject
2020-05-17 20:09:55,129 [stat.AP] Created feed <Feed [stat.AP] with 14 articles>
2020-05-17 20:09:55,130 [cs.LG] Collecting subject
2020-05-17 20:09:56,534 [cs.LG] Created feed <Feed [cs.LG] with 140 articles>
2020-05-17 20:09:56,535 [stat.ML] Collecting subject
2020-05-17 20:09:57,701 [stat.ML] Created feed <Feed [stat.ML] with 68 articles>
...
2020-05-17 20:09:57,709 [cs.CV] Final result: pre 63, post 33; reduction 30 (47.6%)
2020-05-17 20:09:57,709 [cs.CL] Final result: pre 62, post 44; reduction 18 (29.0%)
2020-05-17 20:09:57,709 [cs.SI] Final result: pre 22, post 11; reduction 11 (50.0%)
2020-05-17 20:09:57,709 [nucl-th] Final result: pre 16, post 10; reduction 6 (37.5%)
2020-05-17 20:09:57,709 [stat.AP] Final result: pre 14, post 8; reduction 6 (42.9%)
2020-05-17 20:09:57,710 [cs.LG] Final result: pre 140, post 74; reduction 66 (47.1%)
2020-05-17 20:09:57,710 [stat.ML] Final result: pre 68, post 7; reduction 61 (89.7%)
...
2020-05-17 20:09:57,715 TOTAL Final result: pre 385, post 187; reduction 198 (51.4%)
```
