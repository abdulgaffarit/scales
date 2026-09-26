"""
Protects the hand-edited occupation catalog from accidental regeneration.

data/jobs.csv and data/job_soc.csv are the source of truth for which occupations
exist, their URL slugs and their BLS SOC codes. They have been corrected by hand
(retired duplicate slugs, updated SOC codes, occupations without BLS annual data),
and the legacy generator scripts do not know about those corrections.

Each legacy generator calls require_force() before doing any work. It exits
unless data/jobs.csv is missing or --force was passed explicitly.

Wage figures are refreshed separately by scripts/fetch_oews.py, which only
writes data/national_wages.csv, data/state_wages.csv and data/oews_meta.json
and never touches the catalog.
"""

import sys
from pathlib import Path

JOBS_CSV = Path(__file__).resolve().parent / "data" / "jobs.csv"
FORCE_FLAG = "--force"


def force_requested(argv=None):
    return FORCE_FLAG in (sys.argv if argv is None else argv)


def require_force(script_name, also_writes=()):
    """Exit with an explanation unless it is safe or explicitly forced to overwrite jobs.csv."""
    if not JOBS_CSV.exists():
        return
    if force_requested():
        print(f"⚠️  {script_name}: {FORCE_FLAG} given — data/jobs.csv will be overwritten.")
        return
    extra = "".join(f"\n  - data/{name}" for name in also_writes)
    sys.exit(
        f"❌ {script_name} refused to run: data/jobs.csv already exists.\n\n"
        "data/jobs.csv and data/job_soc.csv are the edited source of truth for the occupation\n"
        "catalog: which occupations exist, their URL slugs and their BLS SOC codes.\n"
        f"Running this script would replace:\n  - data/jobs.csv{extra}\n"
        "and can bring back retired slugs, outdated SOC codes and removed occupations.\n\n"
        "To refresh BLS wages, run scripts/fetch_oews.py instead (it never touches jobs.csv).\n"
        f"Use {FORCE_FLAG} only when you intend to regenerate the whole occupation catalog,\n"
        "then re-apply data/job_soc.csv and data/legacy_slugs.csv before building."
    )
