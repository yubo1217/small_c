#!/bin/bash
# 將 report.md 轉換為 report.pdf
# 需要安裝：sudo dnf install pandoc texlive-xetex texlive-collection-langchinese

set -e
cd "$(dirname "$0")"

pandoc report.md \
  -o report.pdf \
  --pdf-engine=xelatex \
  --include-in-header=header.tex \
  --highlight-style=tango \
  -V papersize=a4 \
  -V linestretch=1.3

echo "Done: docs/report.pdf"
