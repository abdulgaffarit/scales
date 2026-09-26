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

import os

import openpyxl

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BASE = "https://www.bls.gov/oes/special-requests"
# bls.gov rejects anonymous scripted requests; it asks for contact info in the
# User-Agent. Set the BLS_CONTACT secret (an email) to use it.
CONTACT = os.environ.get("BLS_CONTACT") or "https://github.com/abdulgaffarit/scales"
HEADER_SETS = [
    {"User-Agent": f"usasalaries-data-refresh ({CONTACT})", "Accept": "*/*"},
    {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.bls.gov/oes/tables.htm"},
]
FLAT = "https://download.bls.gov/pub/time.series/oe/oe.data.0.Current"
# State FIPS codes for OEWS time-series area codes (FIPS + "00000")
FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10",
        "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
        "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
        "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35",
        "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
        "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
        "WV": "54", "WI": "55", "WY": "56"}
# OEWS time-series datatype codes
DATATYPE = {"01": "tot_emp", "04": "a_mean", "11": "a_pct10", "12": "a_pct25", "13": "a_median",
            "14": "a_pct75", "15": "a_pct90", "17": "loc_quotient"}
FIELDS = ["a_mean", "a_pct10", "a_pct25", "a_median", "a_pct75", "a_pct90"]
# BLS caps top-coded wages: "#" means >= $239,200/yr
TOP_CODE = 239200


def open_url(url):
    """Return an open response, trying each header set; None if all fail."""
    for headers in HEADER_SETS:
        for attempt in range(2):
            try:
                return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300)
            except Exception as e:  # noqa: BLE001
                print(f"  {url} [{headers['User-Agent'][:24]}]: {e}")
                if "404" in str(e):
                    return None
                time.sleep(2 ** (attempt + 1))
    return None


def download(url):
    r = open_url(url)
    return r.read() if r else None


RAW_DIR = DATA_DIR / "raw"


def fetch_release(kind):
    """Newest release first: a manually uploaded data/raw/oesmYY{kind}.zip wins
    (bls.gov blocks cloud IPs), else download. Returns (year, rows) or (None, None)."""
    this_year = date.today().year
    for yy in range(this_year - 2000, this_year - 2000 - 3, -1):
        local = RAW_DIR / f"oesm{yy:02d}{kind}.zip"
        if local.exists():
            print(f"Using {local}")
            blob = local.read_bytes()
        else:
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


def from_flat_file(socs, states):
    """Fallback: stream the OEWS time-series file (all areas, current release)."""
    print(f"Fetching {FLAT}")
    r = open_url(FLAT)
    if not r:
        return None
    area_state = {FIPS[a] + "00000": a for a in states if a in FIPS}
    occ = {s.replace("-", ""): s for s in socs}
    nat, st, year = {}, {}, 0
    for raw in io.TextIOWrapper(r, encoding="utf-8"):
        sid = raw[:30].strip()
        # OEU + N|S + area(7) + industry(6) + occupation(6) + datatype(2)
        if len(sid) != 25 or not sid.startswith("OEU"):
            continue
        dt = DATATYPE.get(sid[23:25])
        soc = occ.get(sid[17:23])
        if not dt or not soc or sid[11:17] != "000000":
            continue
        parts = raw.split("\t")
        value = parts[3].strip() if len(parts) > 3 else ""
        year = max(year, int(parts[1]))
        if sid[3] == "N":
            nat.setdefault(soc, {})[dt] = value
        elif sid[3] == "S" and sid[4:11] in area_state:
            st.setdefault((soc, area_state[sid[4:11]]), {})[dt] = value
    return year, nat, st


def num_or_blank(v):
    return num(v) if v not in ("-", "") else ""


def write_outputs(year, nat, st):
    with open(DATA_DIR / "national_wages.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["soc", "tot_emp"] + FIELDS)
        for soc in sorted(nat):
            w.writerow([soc, num_or_blank(nat[soc].get("tot_emp"))] + [num_or_blank(nat[soc].get(k)) for k in FIELDS])
    with open(DATA_DIR / "state_wages.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["soc", "state", "tot_emp", "loc_quotient"] + FIELDS)
        for key in sorted(st):
            d = st[key]
            w.writerow(list(key) + [num_or_blank(d.get("tot_emp")), (d.get("loc_quotient") or "").strip()]
                       + [num_or_blank(d.get(k)) for k in FIELDS])
    (DATA_DIR / "oews_meta.json").write_text(json.dumps(
        {"release": f"May {year}", "fetched": date.today().isoformat()}, indent=2) + "\n")
    print(f"national_wages.csv: {len(nat)} occupations; state_wages.csv: {len(st)} occupation/state rows")


def main():
    socs = {r["soc"] for r in csv.DictReader(open(DATA_DIR / "job_soc.csv"))}
    states = {r["abbreviation"] for r in csv.DictReader(open(DATA_DIR / "states.csv"))}

    year, rows = fetch_release("nat")
    if rows is None:
        flat = from_flat_file(socs, states)
        if not flat:
            # Not fatal: the site builds from existing data/estimates. Surface it as a warning.
            print("::warning::bls.gov blocked the download (it rejects cloud IPs). Download "
                  "oesmYYnat.zip and oesmYYst.zip from https://www.bls.gov/oes/tables.htm in a "
                  "browser and commit them to data/raw/ — this workflow will parse them.")
            return
        write_outputs(*flat)
        return
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
