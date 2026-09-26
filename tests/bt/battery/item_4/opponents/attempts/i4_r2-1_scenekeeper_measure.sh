#!/bin/bash
# Item 4 round r2-1 scene-keeper: resolve each candidate with pip --dry-run --report (nothing is installed),
# then sum the sizes of the resolved files from the PyPI JSON metadata (read only). Log: measure_<pkg>.log
for pkg in lumibot hikyuu zvt; do
  s=$(date -u +%FT%TZ)
  echo "start $s" > measure_$pkg.log
  ./probe_venv/bin/pip install --dry-run --ignore-installed --report report_$pkg.json $pkg >> measure_$pkg.log 2>&1
  echo "rc=$? end $(date -u +%FT%TZ)" >> measure_$pkg.log
done
