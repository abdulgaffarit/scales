"""
Download BLS OEWS (Occupational Employment and Wage Statistics) national and
state files and extract the occupations listed in data/job_soc.csv.

Writes:
  data/national_wages.csv  soc,tot_emp,a_mean,a_pct10,a_pct25,a_median,a_pct75,a_pct90
  data/state_wages.csv     soc,state,tot_emp,loc_quotient,a_mean,a_pct10,a_pct25,a_median,a_pct75,a_pct90
  data/oews_meta.json      {"release": "May 2025", "fetched": "..."}

Runs in GitHub Actions (bls.gov is not reachable from every network).
Usage: python scripts/fetch_oews.py
"""

import csv
import io
import json
import sys
import time
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import openpyxl

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASE = "https://www.bls.gov/oes/special-requests"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/zip,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bls.gov/oes/tables.htm",
}
FIELDS = ["a_mean", "a_pct10", "a_pct25", "a_median", "a_pct75", "a_pct90"]
# BLS caps top-coded wages: "#" means >= $239,200/yr
TOP_CODE = 239200


def download(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            print(f"  {url}: {e}")
            time.sleep(2 ** (attempt + 1))
    return None


def fetch_release(kind):
    """Try the newest release first. Returns (year, rows) or (None, None)."""
    this_year = date.today().year
    for yy in range(this_year - 2000, this_year - 2000 - 3, -1):
        url = f"{BASE}/oesm{yy:02d}{kind}.zip"
        print(f"Fetching {url}")
        blob = download(url)
        if not blob:
            continue
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
            wb = openpyxl.load_workbook(io.BytesIO(z.read(name)), read_only=True)
            rows = wb.worksheets[0].iter_rows(values_only=True)
            header = [str(h).strip().lower() for h in next(rows)]
            return 2000 + yy, (dict(zip(header, r)) for r in rows)
    return None, None


def num(v):
    if v is None:
        return ""
    s = str(v).strip().replace(",", "")
    if s == "#":
        return str(TOP_CODE)
    try:
        return str(round(float(s)))
    except ValueError:
        return ""  # "*" / "**" = not released


def main():
    socs = {r["soc"] for r in csv.DictReader(open(DATA_DIR / "job_soc.csv"))}
    states = {r["abbreviation"] for r in csv.DictReader(open(DATA_DIR / "states.csv"))}

    year, rows = fetch_release("nat")
    if rows is None:
        sys.exit("Could not download OEWS national file")
    nat = []
    for r in rows:
        if r.get("occ_code") in socs and str(r.get("o_group", "")).lower() == "detailed":
            nat.append([r["occ_code"], num(r.get("tot_emp"))] + [num(r.get(f)) for f in FIELDS])
    with open(DATA_DIR / "national_wages.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["soc", "tot_emp"] + FIELDS)
        w.writerows(sorted(nat))
    print(f"national_wages.csv: {len(nat)} occupations")

    st_year, rows = fetch_release("st")
    if rows is None:
        sys.exit("Could not download OEWS state file")
    out = []
    for r in rows:
        if r.get("occ_code") in socs and r.get("prim_state") in states:
            if str(r.get("o_group", "detailed")).lower() != "detailed":
                continue
            out.append([r["occ_code"], r["prim_state"], num(r.get("tot_emp")),
                        str(r.get("loc_quotient") or "").strip()] + [num(r.get(f)) for f in FIELDS])
    with open(DATA_DIR / "state_wages.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["soc", "state", "tot_emp", "loc_quotient"] + FIELDS)
        w.writerows(sorted(out))
    print(f"state_wages.csv: {len(out)} occupation/state rows")

    (DATA_DIR / "oews_meta.json").write_text(json.dumps(
        {"release": f"May {min(year, st_year)}", "fetched": date.today().isoformat()}, indent=2) + "\n")


if __name__ == "__main__":
    main()
