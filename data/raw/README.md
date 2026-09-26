# Manual BLS OEWS upload

bls.gov blocks downloads from GitHub Actions runners (HTTP 403), so the
"Refresh BLS OEWS Data" workflow reads these files when present.

1. Open https://www.bls.gov/oes/tables.htm in a browser.
2. Download the **National** and **State** XLS zip files for the latest May release
   (e.g. `oesm25nat.zip` and `oesm25st.zip`). Keep the original file names.
3. Upload both to this folder (GitHub → Add file → Upload files) and commit to `main`.

The workflow parses them into `data/national_wages.csv` and `data/state_wages.csv`,
commits the CSVs, and the next deploy builds state pages from real BLS data.
