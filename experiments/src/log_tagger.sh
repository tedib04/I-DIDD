#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="${SCRIPT_DIR}/../data/not_tagged"
OUTPUT_DIR="${SCRIPT_DIR}/../data/tagged"

rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

for input_path in "${INPUT_DIR}"/*.xes; do
  filename=$(basename "${input_path}" .xes)
  output_path="${OUTPUT_DIR}/${filename}_tagged.xes"
  echo "Tagging ${filename}.xes → ${filename}_tagged.xes"
  python "log_tagger.py" "${input_path}" "${output_path}"
done
