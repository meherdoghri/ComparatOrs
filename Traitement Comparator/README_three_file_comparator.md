# File Comparator (2 or 3 files)

Fast and secure CLI tool to detect changes across 2 or 3 versions of the same file.

## Run

```bash
# Compare 2 files
python tools/three_file_comparator.py <v1_file> <v2_file>

# Compare 3 files
python tools/three_file_comparator.py <v1_file> <v2_file> <v3_file>
```

## Useful options

- `--show-diff` : show unified diffs for each pair.
- `--context 5` : number of context lines in unified diff.
- `--json` : output JSON instead of human-readable text.
- `--strip-trailing-space` : ignore trailing spaces in text comparison.
- `--max-size-mb 100` : increase safe size limit for text diff.
- `--allow-large` : allow very large files.

## Example

```bash
# 2-file comparison
python tools/three_file_comparator.py \
  hr-design-center-7.40.05002.00000/build.txt \
  hr-design-center-7.50.01003.00000/build.txt

# 3-file comparison
python tools/three_file_comparator.py \
  hr-design-center-7.40.05002.00000/build.txt \
  hr-design-center-7.50.01003.00000/build.txt \
  hr-design-center-7.50.01003.00000/F_Web.xml
```

For true version comparison, pass the same logical file across 2 or 3 versions.
