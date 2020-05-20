# ArXiv.org RSS Scrubber

The `arxivrss` package is a simple tool that collectively deduplicates multiple [arXiv.org](https://arxiv.org) RSS feeds and then reformats the output. The resulting feeds are dumped into an output directory specified using the argument `-o`. From the help:

```
$ python -m arxivrss -h
usage: arxivrss.py [-h] -o DIR SUBJ [SUBJ ...]

positional arguments:
  SUBJ

optional arguments:
  -h, --help  show this help message and exit
  -o DIR      output directory
```

You can execute the package directly via `python -m arxivrss`.
I run the package via [crontab][] on [my web server][].

```
$  python -m arxivrss -o output cs.CV cs.CL cs.SI nucl-th stat.AP cs.LG stat.ML
2020-05-19 22:00:44,599 [cs.CV] Collecting subject
2020-05-19 22:00:46,027 [cs.CL] Collecting subject
2020-05-19 22:00:47,360 [cs.SI] Collecting subject
2020-05-19 22:00:48,704 [nucl-th] Collecting subject
2020-05-19 22:00:49,447 [stat.AP] Collecting subject
2020-05-19 22:00:50,282 [cs.LG] Collecting subject
2020-05-19 22:00:52,078 [stat.ML] Collecting subject
2020-05-19 22:00:53,076 [cs.CV] Removing 33 UPDATED articles
2020-05-19 22:00:53,083 [cs.CL] Removing 17 UPDATED articles
2020-05-19 22:00:53,087 [cs.SI] Removing 3 UPDATED articles
2020-05-19 22:00:53,088 [nucl-th] Removing 5 UPDATED articles
2020-05-19 22:00:53,088 [stat.AP] Removing 3 UPDATED articles
2020-05-19 22:00:53,091 [cs.LG] Removing 62 UPDATED articles
2020-05-19 22:00:53,108 [stat.ML] Removing 43 UPDATED articles
2020-05-19 22:00:53,115 [cs.CV] Removing 4 CROSS POSTED articles
2020-05-19 22:00:53,118 [cs.CL] Removing 5 CROSS POSTED articles
2020-05-19 22:00:53,119 [cs.SI] Removing 0 CROSS POSTED articles
2020-05-19 22:00:53,119 [nucl-th] Removing 0 CROSS POSTED articles
2020-05-19 22:00:53,120 [stat.AP] Removing 0 CROSS POSTED articles
2020-05-19 22:00:53,121 [cs.LG] Removing 22 CROSS POSTED articles
2020-05-19 22:00:53,126 [stat.ML] Removing 28 CROSS POSTED articles
2020-05-19 22:00:53,130 [cs.CV] Removing 0 DUPLICATE articles
2020-05-19 22:00:53,131 [cs.CL] Removing 0 DUPLICATE articles
2020-05-19 22:00:53,132 [cs.SI] Removing 0 DUPLICATE articles
2020-05-19 22:00:53,132 [nucl-th] Removing 0 DUPLICATE articles
2020-05-19 22:00:53,133 [stat.AP] Removing 0 DUPLICATE articles
2020-05-19 22:00:53,134 [cs.LG] Removing 9 DUPLICATE articles
2020-05-19 22:00:53,137 [stat.ML] Removing 9 DUPLICATE articles
2020-05-19 22:00:53,139 [cs.CV] Final result: pre 80, post 43; reduction 37 (46.2%)
2020-05-19 22:00:53,139 [cs.CL] Final result: pre 53, post 31; reduction 22 (41.5%)
2020-05-19 22:00:53,140 [cs.SI] Final result: pre 9, post 6; reduction 3 (33.3%)
2020-05-19 22:00:53,140 [nucl-th] Final result: pre 12, post 7; reduction 5 (41.7%)
2020-05-19 22:00:53,140 [stat.AP] Final result: pre 13, post 10; reduction 3 (23.1%)
2020-05-19 22:00:53,141 [cs.LG] Final result: pre 154, post 61; reduction 93 (60.4%)
2020-05-19 22:00:53,141 [stat.ML] Final result: pre 84, post 4; reduction 80 (95.2%)
2020-05-19 22:00:53,143 [cs.CV] Writing to output/cs.CV.xml
2020-05-19 22:00:53,148 [cs.CL] Writing to output/cs.CL.xml
2020-05-19 22:00:53,149 [cs.SI] Writing to output/cs.SI.xml
2020-05-19 22:00:53,150 [nucl-th] Writing to output/nucl-th.xml
2020-05-19 22:00:53,151 [stat.AP] Writing to output/stat.AP.xml
2020-05-19 22:00:53,154 [cs.LG] Writing to output/cs.LG.xml
2020-05-19 22:00:53,156 [stat.ML] Writing to output/stat.ML.xml
2020-05-19 22:00:53,156 [TOTAL] Final result: pre 405, post 162; reduction 243 (60.0%)
```

[crontab]: https://crontab.guru
[my web server]: https://tshafer.com
