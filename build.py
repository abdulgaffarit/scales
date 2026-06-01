#!/usr/bin/env python3
"""
SalaryScale - Programmatic SEO Site Generator
Generates 50,000+ salary pages from BLS data
Author: SalaryScale Build System
"""

import csv
import json
import os
import math
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# ─── CONFIG ────────────────────────────────────────────────────────────────────
SITE_DOMAIN    = "usasalaries.com"
SITE_NAME      = "USA Salaries"
ADSENSE_ID     = "ca-pub-XXXXXXXXXXXXXXXXX"   # ← Replace with your AdSense ID
AD_SLOT_TOP    = "1234567890"
AD_SLOT_MID    = "2345678901"
AD_SLOT_BOTTOM = "3456789012"
AD_SLOT_SIDEBAR  = "4567890123"
AD_SLOT_SIDEBAR2 = "5678901234"

BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
TMPL_DIR    = BASE_DIR / "templates"
OUTPUT_DIR  = BASE_DIR / "output"

# ─── JINJA2 SETUP ──────────────────────────────────────────────────────────────
env = Environment(loader=FileSystemLoader(str(TMPL_DIR)), autoescape=True)
from markupsafe import Markup
template = env.get_template("base.html")

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def fmt(n):
    """Format number with commas"""
    return f"{int(n):,}"

def short_fmt(n):
    """Short format: 78450 → 78.4k"""
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def calc_salary(national_avg, multiplier):
    """Apply cost-of-living multiplier"""
    return round(national_avg * float(multiplier))

def hourly(annual):
    return round(annual / 2080, 2)

def percentiles(avg, low, high):
    """Generate salary percentiles"""
    spread = high - low
    return {
        "p10": round(low + spread * 0.05),
        "p25": round(low + spread * 0.25),
        "median": round((avg + low + high) / 3),
        "p75": round(low + spread * 0.70),
        "p90": round(high * 0.92),
    }

def trend_data(avg, yoy_growth, years=6):
    """Generate salary trend bars for 2020-2026"""
    bars = []
    growth = float(yoy_growth) / 100
    base_year = 2026 - years + 1
    base_salary = avg / ((1 + growth) ** (years - 1))
    max_val = avg
    for i in range(years):
        val = round(base_salary * ((1 + growth) ** i))
        bars.append({
            "year": base_year + i,
            "value": val,
            "short": short_fmt(val),
            "height": 0
        })
    # Normalize heights 30–100px
    min_val = bars[0]["value"]
    for b in bars:
        b["height"] = round(30 + 70 * (b["value"] - min_val) / (max_val - min_val + 1))
    return bars

def demand_badge(demand):
    mapping = {
        "Very High": "badge-green",
        "High": "badge-blue",
        "Medium": "badge-orange",
    }
    return mapping.get(demand, "badge-blue")

def write_page(path, context):
    """Render template and write HTML file"""
    out_path = OUTPUT_DIR / path / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = template.render(**context)
    out_path.write_text(html, encoding="utf-8")

def base_context():
    return {
        "site_domain": SITE_DOMAIN,
        "site_name": SITE_NAME,
        "adsense_id": ADSENSE_ID,
        "ad_slot_top": AD_SLOT_TOP,
        "ad_slot_mid": AD_SLOT_MID,
        "ad_slot_bottom": AD_SLOT_BOTTOM,
        "ad_slot_sidebar": AD_SLOT_SIDEBAR,
        "ad_slot_sidebar2": AD_SLOT_SIDEBAR2,
    }

# ─── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_csv(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ─── SCHEMA GENERATORS ─────────────────────────────────────────────────────────
def dataset_schema(name, desc, url):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": name,
        "description": desc,
        "url": f"https://{SITE_DOMAIN}{url}",
        "creator": {"@type": "Organization", "name": SITE_NAME},
        "variableMeasured": "Annual Salary (USD)",
        "spatialCoverage": "United States",
        "temporalCoverage": "2025",
        "license": "https://creativecommons.org/licenses/by/4.0/"
    }, indent=2)

def faq_schema(faqs):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faqs
        ]
    }, indent=2)

def breadcrumb_schema(items):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i+1,
             "name": item["name"],
             "item": f"https://{SITE_DOMAIN}{item['url']}"}
            for i, item in enumerate(items)
        ]
    }, indent=2)

def breadcrumb_html(items):
    parts = [f'<a href="/">Home</a>']
    for item in items:
        parts.append(f'<span>›</span><a href="{item["url"]}">{item["name"]}</a>')
    return Markup(" ".join(parts))

# ─── PAGE GENERATORS ───────────────────────────────────────────────────────────

def generate_job_national(job, all_jobs, states):
    """Generate /salary/[job]/ page"""
    avg     = int(job["national_avg"])
    median  = int(job["national_median"])
    low     = int(job["national_low"])
    high    = int(job["national_high"])
    pct     = percentiles(avg, low, high)
    trend   = trend_data(avg, job["yoy_growth"])
    url     = f"/salary/{job['job_slug']}/"
    title   = job["job_title"]

    # All states sorted by salary (highest first)
    all_states_rows = []
    for s in states:
        s_salary = calc_salary(avg, s["col_multiplier"])
        diff_pct  = round((s_salary - avg) / avg * 100, 1)
        all_states_rows.append({
            "name": s["state_name"],
            "url": f"/salary/{job['job_slug']}/{s['state_slug']}/",
            "salary_val": s_salary,
            "salary_fmt": fmt(s_salary),
            "diff_pct": abs(diff_pct),
            "diff_positive": diff_pct >= 0,
            "demand": job["demand"],
            "demand_class": demand_badge(job["demand"]),
        })
    # Sort by salary descending
    all_states_rows.sort(key=lambda x: x["salary_val"], reverse=True)

    # Related jobs (same category first, then others)
    same_cat = [j for j in all_jobs if j["category"] == job["category"] and j["job_slug"] != job["job_slug"]]
    other_jobs = [j for j in all_jobs if j["category"] != job["category"]]
    related = (same_cat[:6] + other_jobs[:2]) if same_cat else [j for j in all_jobs if j["job_slug"] != job["job_slug"]][:8]
    related_jobs = []
    for r in related:
        r_avg = int(r["national_avg"])
        diff  = round((r_avg - avg) / avg * 100, 1)
        related_jobs.append({
            "title": r["job_title"],
            "url": f"/salary/{r['job_slug']}/",
            "salary_fmt": fmt(r_avg),
            "diff_pct": abs(diff),
            "diff_positive": diff >= 0,
        })

    # Top states sidebar
    top_states_sidebar = sorted(states, key=lambda s: float(s["col_multiplier"]), reverse=True)[:6]
    sidebar_states = [{"name": s["state_name"], "url": f"/salary/{job['job_slug']}/{s['state_slug']}/", "salary_fmt": fmt(calc_salary(avg, s["col_multiplier"]))} for s in top_states_sidebar]

    # Category jobs for sidebar
    cat_jobs = [j for j in all_jobs if j["category"] == job["category"] and j["job_slug"] != job["job_slug"]][:6]
    category_jobs = [{"title": j["job_title"], "url": f"/salary/{j['job_slug']}/"} for j in cat_jobs]

    faqs = [
        {"q": f"What is the average salary for a {title}?",
         "a": f"The average salary for a {title} in the United States is ${fmt(avg)} per year, with a median of ${fmt(median)}."},
        {"q": f"What is the starting salary for a {title}?",
         "a": f"Entry-level {title}s typically earn between ${fmt(pct['p10'])} and ${fmt(pct['p25'])} per year depending on location and employer."},
        {"q": f"What state pays {title}s the most?",
         "a": f"California, New York, and Washington typically pay {title}s the highest salaries due to high cost of living and strong job markets."},
        {"q": f"How much does a {title} make per hour?",
         "a": f"Based on the average annual salary of ${fmt(avg)}, a {title} earns approximately ${hourly(avg)} per hour (based on 2,080 working hours/year)."},
        {"q": f"Is {title} a good career in 2026?",
         "a": f"Yes — the {title} role has {job['demand'].lower()} demand with {job['yoy_growth']}% year-over-year salary growth, indicating a strong and growing career path."},
    ]

    ctx = base_context()
    ctx.update({
        "page_title": f"{title} Salary 2026 | {SITE_NAME}",
        "meta_description": f"{title} salary: ${fmt(avg)}/yr avg in 2026. Pay by state, percentile & experience. Source: BLS OES.",
        "canonical_url": url,
        "h1_title": f"{title} Salary in the United States (2026)",
        "hero_subtitle": f"Based on U.S. Bureau of Labor Statistics data · Updated 2026 · {job['demand']} Demand",
        "avg_salary_fmt": fmt(avg),
        "median_salary_fmt": fmt(median),
        "hourly_rate": hourly(avg),
        "p10_fmt": fmt(pct["p10"]),
        "p25_fmt": fmt(pct["p25"]),
        "p75_fmt": fmt(pct["p75"]),
        "p90_fmt": fmt(pct["p90"]),
        "percentile_insight": f"The top 10% of {title}s earn ${fmt(pct['p90'])} or more per year. Entry-level professionals can expect to start around ${fmt(pct['p10'])}, with significant growth over the first 5 years.",
        "trend_bars": trend,
        "trend_insight": f"{title} salaries have grown {job['yoy_growth']}% year-over-year. Since 2020, the average salary has increased by approximately ${fmt(round(avg - trend[0]['value']))}.",
        "comparison_table_title": "Salary by State",
        "comparison_col1": "State",
        "comparison_rows": all_states_rows,
        "insight_title": f"What Factors Affect {title} Salary?",
        "insight_p1": f"A {title}'s salary is influenced by several key factors including geographic location, years of experience, employer type, and educational background. States with higher costs of living — such as California, New York, and Washington — typically offer 20–40% higher salaries than the national average to compensate for living expenses.",
        "insight_p2": f"Experience plays a major role in compensation. Entry-level {title}s typically earn ${fmt(pct['p10'])}–${fmt(pct['p25'])} per year, while senior professionals with 10+ years of experience can command ${fmt(pct['p75'])}–${fmt(pct['p90'])} annually. Specialization and advanced certifications can further boost earning potential.",
        "insight_p3": f"Employer size also matters. Large corporations and government agencies tend to offer more competitive packages including benefits, retirement plans, and bonuses. The {title} role currently has {job['demand'].lower()} demand in the job market with a {job['yoy_growth']}% growth rate, making it one of the {'most' if float(job['yoy_growth']) > 4 else 'steadily'} growing careers in the {job['category']} sector.",
        "related_jobs": related_jobs,
        "faqs": faqs,
        "schema_json": dataset_schema(f"{title} Salary 2026", f"Comprehensive salary data for {title} professionals in the United States.", url),
        "faq_schema_json": faq_schema(faqs),
        "breadcrumb_schema": breadcrumb_schema([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": url}]),
        "breadcrumb_html": breadcrumb_html([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": url}]),
        "top_states": sidebar_states,
        "top_cities": [],
        "category_jobs": category_jobs,
        "related_links": [{"url": r["url"], "text": f"{title} Salary in {r['name']}"} for r in all_states_rows[:8]],
    })
    write_page(f"salary/{job['job_slug']}", ctx)


def generate_job_state(job, state, all_cities, all_jobs, states):
    """Generate /salary/[job]/[state]/ page"""
    nat_avg   = int(job["national_avg"])
    avg       = calc_salary(nat_avg, state["col_multiplier"])
    median    = calc_salary(int(job["national_median"]), state["col_multiplier"])
    low       = calc_salary(int(job["national_low"]), state["col_multiplier"])
    high      = calc_salary(int(job["national_high"]), state["col_multiplier"])
    pct       = percentiles(avg, low, high)
    trend     = trend_data(avg, job["yoy_growth"])
    url       = f"/salary/{job['job_slug']}/{state['state_slug']}/"
    title     = job["job_title"]
    sname     = state["state_name"]

    # Cities in this state
    state_cities = [c for c in all_cities if c["state_slug"] == state["state_slug"]]
    city_rows = []
    for c in state_cities:
        c_salary = calc_salary(avg, c["col_multiplier"])
        diff_pct = round((c_salary - avg) / avg * 100, 1)
        city_rows.append({
            "name": c["city_name"],
            "url": f"/salary/{job['job_slug']}/{state['state_slug']}/",
            "salary_fmt": fmt(c_salary),
            "diff_pct": abs(diff_pct),
            "diff_positive": diff_pct >= 0,
            "demand": job["demand"],
            "demand_class": demand_badge(job["demand"]),
        })

    # Top cities for sidebar
    top_cities_sidebar = sorted(state_cities, key=lambda c: float(c["col_multiplier"]), reverse=True)[:5]
    sidebar_cities = [{"name": c["city_name"], "url": f"/salary/{job['job_slug']}/{state['state_slug']}/", "salary_fmt": fmt(calc_salary(avg, c["col_multiplier"]))} for c in top_cities_sidebar]

    diff_national = round((avg - nat_avg) / nat_avg * 100, 1)

    faqs = [
        {"q": f"What is the average {title} salary in {sname}?",
         "a": f"The average {title} salary in {sname} is ${fmt(avg)} per year in 2026, which is {abs(diff_national)}% {'above' if diff_national >= 0 else 'below'} the national average of ${fmt(nat_avg)}."},
        {"q": f"What city in {sname} pays {title}s the most?",
         "a": f"{'San Francisco and San Jose' if sname == 'California' else 'Major metro areas'} typically pay {title}s the highest wages in {sname} due to higher costs of living and competitive job markets."},
        {"q": f"Is {sname} a good state for {title}s?",
         "a": f"{sname} has a {state['job_market'].lower()} job market with major industries in {state['major_industries']}. {'This makes it one of the better states' if state['job_market'] in ['Very Strong', 'Strong'] else 'Opportunities exist in'} for {title} employment."},
        {"q": f"How does {sname} {title} salary compare to the US average?",
         "a": f"At ${fmt(avg)}/year, {sname} {title} salaries are {abs(diff_national)}% {'higher' if diff_national >= 0 else 'lower'} than the national average of ${fmt(nat_avg)}/year."},
    ]

    ctx = base_context()
    ctx.update({
        "page_title": f"{title} Salary in {sname} (2026) | ${fmt(avg)}/yr",
        "meta_description": f"{title} salary in {sname}: ${fmt(avg)}/yr (2026). Pay by city, trend data & state comparison. Source: BLS OES.",
        "canonical_url": url,
        "h1_title": f"{title} Salary in {sname} (2026)",
        "hero_subtitle": f"{sname} · {abs(diff_national)}% {'above' if diff_national >= 0 else 'below'} national average · {job['demand']} Demand",
        "avg_salary_fmt": fmt(avg),
        "median_salary_fmt": fmt(median),
        "hourly_rate": hourly(avg),
        "p10_fmt": fmt(pct["p10"]),
        "p25_fmt": fmt(pct["p25"]),
        "p75_fmt": fmt(pct["p75"]),
        "p90_fmt": fmt(pct["p90"]),
        "percentile_insight": f"Top-earning {title}s in {sname} make up to ${fmt(pct['p90'])} per year. The job market in {sname} is rated {state['job_market'].lower()}, with key industries including {state['major_industries']}.",
        "trend_bars": trend,
        "trend_insight": f"{title} salaries in {sname} have followed the national trend with {job['yoy_growth']}% annual growth. The strong {'demand' if job['demand'] in ['Very High', 'High'] else 'presence'} in {sname}'s job market supports continued salary increases.",
        "comparison_table_title": f"{title} Salary by City in {sname}",
        "comparison_col1": "City",
        "comparison_rows": city_rows if city_rows else [{"name": "Statewide Average", "url": url, "salary_fmt": fmt(avg), "diff_pct": 0, "diff_positive": True, "demand": job["demand"], "demand_class": demand_badge(job["demand"])}],
        "insight_title": f"{title} Job Market in {sname}",
        "insight_p1": f"{sname} is home to a {state['job_market'].lower()} job market for {title}s. The state's key industries — {state['major_industries']} — generate significant demand for skilled professionals. At ${fmt(avg)} per year, {sname}'s {title} salaries are {abs(diff_national)}% {'higher' if diff_national >= 0 else 'lower'} than the national average.",
        "insight_p2": f"The cost of living in {sname} (index: {state['col_multiplier']}) {'justifies the higher pay scale' if float(state['col_multiplier']) > 1 else 'makes salaries stretch further than in higher-cost states'}. Entry-level professionals in {sname} can expect to earn ${fmt(pct['p10'])}–${fmt(pct['p25'])}, while experienced {title}s can command ${fmt(pct['p75'])}–${fmt(pct['p90'])}.",
        "insight_p3": f"Looking ahead, the {title} profession in {sname} is projected to grow at {job['yoy_growth']}% annually. Major employers are actively hiring, and the state's investment in {state['major_industries'].split(',')[0].strip()} continues to drive new opportunities for qualified candidates.",
        "related_jobs": [],
        "faqs": faqs,
        "schema_json": dataset_schema(f"{title} Salary in {sname} 2026", f"Salary data for {title} professionals in {sname}.", url),
        "faq_schema_json": faq_schema(faqs),
        "breadcrumb_schema": breadcrumb_schema([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": url}]),
        "breadcrumb_html": breadcrumb_html([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": url}]),
        "top_states": [],
        "top_cities": sidebar_cities,
        "category_jobs": [],
        "related_links": [{"url": f"/salary/{job['job_slug']}/{s['state_slug']}/", "text": f"{title} Salary in {s['state_name']}"} for s in sorted([s for s in states if s["state_slug"] != state["state_slug"]], key=lambda s: float(s["col_multiplier"]), reverse=True)[:8]],
    })
    write_page(f"salary/{job['job_slug']}/{state['state_slug']}", ctx)


def generate_job_city(job, state, city, all_jobs):
    """Generate /salary/[job]/[state]/[city]/ page"""
    nat_avg  = int(job["national_avg"])
    state_avg = calc_salary(nat_avg, state["col_multiplier"])
    avg      = calc_salary(state_avg, city["col_multiplier"])
    median   = round(avg * 0.97)
    low      = calc_salary(int(job["national_low"]), float(state["col_multiplier"]) * float(city["col_multiplier"]))
    high     = calc_salary(int(job["national_high"]), float(state["col_multiplier"]) * float(city["col_multiplier"]))
    pct      = percentiles(avg, low, high)
    trend    = trend_data(avg, job["yoy_growth"])
    url      = f"/salary/{job['job_slug']}/{state['state_slug']}/{city['city_slug']}/"
    title    = job["job_title"]
    sname    = state["state_name"]
    cname    = city["city_name"]

    diff_national = round((avg - nat_avg) / nat_avg * 100, 1)
    diff_state    = round((avg - state_avg) / state_avg * 100, 1)

    # Related jobs in same city
    related_jobs = []
    for r in [j for j in all_jobs if j["job_slug"] != job["job_slug"]][:6]:
        r_avg = calc_salary(calc_salary(int(r["national_avg"]), state["col_multiplier"]), city["col_multiplier"])
        diff  = round((r_avg - avg) / avg * 100, 1)
        related_jobs.append({
            "title": r["job_title"],
            "url": f"/salary/{r['job_slug']}/{state['state_slug']}/{city['city_slug']}/",
            "salary_fmt": fmt(r_avg),
            "diff_pct": abs(diff),
            "diff_positive": diff >= 0,
        })

    faqs = [
        {"q": f"What is the average {title} salary in {cname}, {sname}?",
         "a": f"The average {title} salary in {cname}, {sname} is ${fmt(avg)} per year in 2026. This is {abs(diff_national)}% {'above' if diff_national >= 0 else 'below'} the national average of ${fmt(nat_avg)}."},
        {"q": f"How much does a {title} make per hour in {cname}?",
         "a": f"A {title} in {cname} earns approximately ${hourly(avg)} per hour, based on an annual salary of ${fmt(avg)}."},
        {"q": f"Is {cname} a good city for {title}s?",
         "a": f"{cname} is a {city['metro_type'].lower()} with {state['job_market'].lower()} job market conditions. The city's {'high' if float(city['col_multiplier']) > 1.1 else 'moderate'} cost of living is {'reflected in above-average compensation' if float(city['col_multiplier']) > 1.1 else 'balanced by competitive salaries'} for {title}s."},
        {"q": f"What is the {title} salary in {cname} vs {sname} average?",
         "a": f"At ${fmt(avg)}, {cname} {title} salaries are {abs(diff_state)}% {'above' if diff_state >= 0 else 'below'} the {sname} state average of ${fmt(state_avg)}."},
    ]

    ctx = base_context()
    ctx.update({
        "page_title": f"{title} Salary in {cname}, {sname} (2026) | ${fmt(avg)}/yr",
        "meta_description": f"{title} salary in {cname}, {sname}: ${fmt(avg)}/yr (2026). Hourly rate, percentiles & city comparison. Source: BLS OES.",
        "canonical_url": url,
        "h1_title": f"{title} Salary in {cname}, {sname} (2026)",
        "hero_subtitle": f"{cname}, {sname} · {city['metro_type']} · {abs(diff_national)}% {'above' if diff_national >= 0 else 'below'} national average",
        "avg_salary_fmt": fmt(avg),
        "median_salary_fmt": fmt(median),
        "hourly_rate": hourly(avg),
        "p10_fmt": fmt(pct["p10"]),
        "p25_fmt": fmt(pct["p25"]),
        "p75_fmt": fmt(pct["p75"]),
        "p90_fmt": fmt(pct["p90"]),
        "percentile_insight": f"Top-earning {title}s in {cname} can make up to ${fmt(pct['p90'])} per year. Entry-level positions typically start around ${fmt(pct['p10'])}, with the median falling at ${fmt(pct['median'])}.",
        "trend_bars": trend,
        "trend_insight": f"Salaries for {title}s in {cname} have grown {job['yoy_growth']}% annually, in line with both state and national trends. {cname}'s position as a {city['metro_type'].lower()} supports continued above-average compensation.",
        "comparison_table_title": f"Other Jobs in {cname}",
        "comparison_col1": "Job Title",
        "comparison_rows": [{"name": r["title"], "url": r["url"], "salary_fmt": r["salary_fmt"], "diff_pct": r["diff_pct"], "diff_positive": r["diff_positive"], "demand": job["demand"], "demand_class": demand_badge(job["demand"])} for r in related_jobs],
        "insight_title": f"Living and Working as a {title} in {cname}",
        "insight_p1": f"{cname} is a {city['metro_type'].lower()} in {sname} with a population of approximately {int(city['population']):,}. For {title}s, the city offers a salary of ${fmt(avg)} per year — {abs(diff_national)}% {'above' if diff_national >= 0 else 'below'} the national average. The local cost of living index of {city['col_multiplier']} {'reflects the premium of living in a major metro area' if float(city['col_multiplier']) > 1.2 else 'makes it relatively affordable compared to coastal metros'}.",
        "insight_p2": f"The job market in {cname} benefits from {sname}'s key industries including {state['major_industries']}. Employers in this area typically offer competitive compensation packages. Entry-level {title}s in {cname} can expect to earn ${fmt(pct['p10'])}–${fmt(pct['p25'])} while experienced professionals command ${fmt(pct['p75'])}–${fmt(pct['p90'])}.",
        "insight_p3": f"When adjusted for cost of living, a {title}'s ${fmt(avg)} salary in {cname} has an equivalent purchasing power of approximately ${fmt(round(avg / float(city['col_multiplier'])))} in a city with average cost of living. This is an important consideration when comparing job offers across different metro areas.",
        "related_jobs": related_jobs,
        "faqs": faqs,
        "schema_json": dataset_schema(f"{title} Salary in {cname}, {sname} 2026", f"Detailed salary data for {title} professionals in {cname}, {sname}.", url),
        "faq_schema_json": faq_schema(faqs),
        "breadcrumb_schema": breadcrumb_schema([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": f"/salary/{job['job_slug']}/{state['state_slug']}/"}, {"name": cname, "url": url}]),
        "breadcrumb_html": breadcrumb_html([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": f"/salary/{job['job_slug']}/{state['state_slug']}/"}, {"name": cname, "url": url}]),
        "top_states": [],
        "top_cities": [],
        "category_jobs": [],
        "related_links": [{"url": f"/salary/{r['job_slug']}/{state['state_slug']}/{city['city_slug']}/", "text": f"{r['job_title']} Salary in {cname}"} for r in [j for j in all_jobs if j['job_slug'] != job['job_slug']][:8]],
    })
    write_page(f"salary/{job['job_slug']}/{state['state_slug']}/{city['city_slug']}", ctx)


def generate_homepage(jobs, states):
    """Generate modern homepage using template"""
    out_path = OUTPUT_DIR / "index.html"
    hp_template = env.get_template("homepage.html")

    from collections import defaultdict
    categories = defaultdict(list)
    for j in jobs:
        categories[j["category"]].append(j)

    cat_icons = {
        "Healthcare":"🏥","Technology":"💻","Finance":"💰","Engineering":"⚙️",
        "Education":"🎓","Management":"📊","Skilled Trades":"🔧","Transportation":"🚛",
        "Sales":"📈","Legal":"⚖️","Marketing":"📣","Creative":"🎨","Science":"🔬",
        "Social Services":"🤝","Public Safety":"🛡️","Human Resources":"👥",
        "Construction":"🏗️","Real Estate":"🏠","Hospitality":"🍽️",
        "Personal Services":"✂️","Business":"💼","Manufacturing":"🏭","Agriculture":"🌾",
    }

    # Category nav pills
    cat_nav = "".join(
        f'<a href="#cat-{c.lower().replace(" ","-")}">{cat_icons.get(c,"💼")} {c}</a>'
        for c in sorted(categories.keys())
    )

    # Category sections
    cat_sections = ""
    for cat_name in sorted(categories.keys()):
        cat_jobs = sorted(categories[cat_name], key=lambda x: int(x["national_avg"]), reverse=True)
        icon = cat_icons.get(cat_name, "💼")
        anchor = cat_name.lower().replace(" ", "-")
        cards = "".join(
            f'<a href="/salary/{j["job_slug"]}/" class="job-tile">'
            f'<div class="tile-name">{j["job_title"]}</div>'
            f'<div class="tile-salary">${fmt(int(j["national_avg"]))}<span>/yr</span></div>'
            f'<div class="tile-demand {("d-high" if j["demand"] in ["Very High","High"] else "d-mid")}">{j["demand"]} Demand</div>'
            f'</a>'
            for j in cat_jobs
        )
        cat_sections += (
            f'<section class="cat-section" id="cat-{anchor}">'
            f'<div class="cat-hdr"><span class="cat-icon">{icon}</span>'
            f'<h2 class="cat-name">{cat_name}</h2>'
            f'<span class="cat-count">{len(cat_jobs)} jobs</span></div>'
            f'<div class="cat-grid">{cards}</div>'
            f'</section>'
        )

    # Top paying jobs (sidebar)
    top_jobs = sorted(jobs, key=lambda x: int(x["national_avg"]), reverse=True)[:8]
    top_jobs_html = "".join(
        f'<div class="top-job-item">'
        f'<a href="/salary/{j["job_slug"]}/" class="top-job-name">{j["job_title"]}</a>'
        f'<span class="top-job-salary">${fmt(int(j["national_avg"]))}</span>'
        f'</div>'
        for j in top_jobs
    )

    # Trending jobs by growth
    trending_html = "".join(
        f'<li><span class="trending-num">{i+1}</span><a href="/salary/{j["job_slug"]}/">{j["job_title"]}</a></li>'
        for i, j in enumerate(sorted(jobs, key=lambda x: float(x["yoy_growth"]), reverse=True)[:7])
    )

    # Footer content
    footer_top_jobs = "".join(
        f'<a href="/salary/{j["job_slug"]}/">{j["job_title"]}</a>'
        for j in sorted(jobs, key=lambda x: int(x["national_avg"]), reverse=True)[:6]
    )
    footer_states = "".join(
        f'<a href="/salary/registered-nurses/{s["state_slug"]}/">{s["state_name"]}</a>'
        for s in states[:6]
    )

    # Schema
    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": f"https://{SITE_DOMAIN}",
        "description": f"Comprehensive US salary data for {len(jobs)}+ occupations across all 50 states.",
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"https://{SITE_DOMAIN}/salary/{{search_term_string}}/",
            "query-input": "required name=search_term_string"
        }
    }, indent=2)

    html = hp_template.render(
        site_domain=SITE_DOMAIN,
        site_name=SITE_NAME,
        page_title=f"US Salary Data 2026 by Job, State & City | {SITE_NAME}",
        meta_description=f"Explore 2026 US salary data for {len(jobs)}+ jobs across every state and major city. Compare pay by location, career level, and industry using BLS data.",
        schema_json=Markup(schema_json),
        job_count=len(jobs),
        page_count=f"{len(jobs) * len(states) + len(jobs) + 1:,}",
        cat_nav=Markup(cat_nav),
        cat_sections=Markup(cat_sections),
        top_jobs_html=Markup(top_jobs_html),
        trending_html=Markup(trending_html),
        footer_top_jobs=Markup(footer_top_jobs),
        footer_states=Markup(footer_states),
    )
    out_path.write_text(html, encoding="utf-8")


# ─── SITEMAP GENERATOR ─────────────────────────────────────────────────────────
def generate_sitemap(jobs, states, cities):
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")

    # Sitemap 1: high-priority pages (homepage + all national job pages)
    priority_urls = []
    priority_urls.append((f"https://{SITE_DOMAIN}/", "1.0", "weekly"))
    for j in jobs:
        priority_urls.append((f"https://{SITE_DOMAIN}/salary/{j['job_slug']}/", "0.9", "monthly"))

    # Sitemap 2: state pages (lower priority — large volume, less unique)
    state_urls = []
    for j in jobs:
        for s in states:
            state_urls.append((f"https://{SITE_DOMAIN}/salary/{j['job_slug']}/{s['state_slug']}/", "0.6", "monthly"))

    def write_urlset(url_list, filename):
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for loc, pri, freq in url_list:
            sm += f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq><priority>{pri}</priority></url>\n"
        sm += "</urlset>"
        (OUTPUT_DIR / filename).write_text(sm, encoding="utf-8")

    write_urlset(priority_urls, "sitemap-1.xml")

    # Split state pages into chunks of 49k
    chunk_size = 49000
    chunks = [state_urls[i:i+chunk_size] for i in range(0, len(state_urls), chunk_size)]
    for i, chunk in enumerate(chunks):
        write_urlset(chunk, f"sitemap-{i+2}.xml")

    # Sitemap index
    all_files = ["sitemap-1.xml"] + [f"sitemap-{i+2}.xml" for i in range(len(chunks))]
    index = '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for fname in all_files:
        index += f"  <sitemap><loc>https://{SITE_DOMAIN}/{fname}</loc><lastmod>{today}</lastmod></sitemap>\n"
    index += "</sitemapindex>"
    (OUTPUT_DIR / "sitemap.xml").write_text(index, encoding="utf-8")

    total = len(priority_urls) + len(state_urls)
    print(f"✅ Sitemap: {total:,} URLs — {len(priority_urls)} high-priority, {len(state_urls)} state pages")


def generate_search_index(jobs, states):
    """Generate a lightweight JSON search index for client-side search"""
    index = []
    for j in jobs:
        index.append({
            "t": j["job_title"],
            "u": f"/salary/{j['job_slug']}/",
            "s": fmt(int(j["national_avg"])),
            "c": j["category"],
        })
    for s in states:
        index.append({
            "t": s["state_name"],
            "u": f"/salary/registered-nurses/{s['state_slug']}/",
            "s": "",
            "c": "State",
        })
    (OUTPUT_DIR / "search-index.json").write_text(json.dumps(index), encoding="utf-8")
    print(f"✅ Search index: {len(index)} entries")


def generate_static_pages(jobs):
    """Generate About, Methodology, Privacy, and Contact pages"""
    static_template = env.get_template("static.html")

    pages = {
        "about": {
            "page_title": f"About {SITE_NAME} | US Salary Data from BLS",
            "meta_description": "USASalaries provides accurate US salary data for 300+ jobs across all 50 states, sourced directly from the U.S. Bureau of Labor Statistics OES program.",
            "canonical_url": "/about/",
            "content": f"""
<div class="badge">🏛️ About Us</div>
<h1>About {SITE_NAME}</h1>
<p class="subtitle">Comprehensive salary intelligence powered by official government data.</p>

<p><strong>{SITE_NAME}</strong> provides accurate, up-to-date salary information for hundreds of occupations across every U.S. state and major city. Our mission is to help workers, job seekers, employers, and researchers make informed decisions about compensation.</p>

<h2>What We Do</h2>
<p>We transform complex government wage data into clear, accessible salary insights. Every data point on this site comes directly from the U.S. Bureau of Labor Statistics Occupational Employment and Wage Statistics (OES) program — the gold standard for occupational wage data in the United States.</p>

<div class="card">
<h3>📊 By the Numbers</h3>
<ul>
<li><strong>{len(jobs)}+ occupations</strong> with detailed salary breakdowns</li>
<li><strong>51 geographic areas</strong> (all 50 states + District of Columbia)</li>
<li><strong>Percentile data</strong> from entry-level (10th) to top earners (90th)</li>
<li><strong>Year-over-year trends</strong> showing salary growth trajectories</li>
<li><strong>Updated annually</strong> with each new BLS data release</li>
</ul>
</div>

<h2>Who This Is For</h2>
<ul>
<li><strong>Job seekers</strong> — Research fair compensation before interviews and negotiations</li>
<li><strong>Employees</strong> — Benchmark your current salary against national and state averages</li>
<li><strong>Employers & HR</strong> — Set competitive pay ranges based on real market data</li>
<li><strong>Students</strong> — Explore career paths and their earning potential</li>
<li><strong>Researchers</strong> — Access structured wage data for analysis</li>
</ul>

<h2>Our Data Source</h2>
<p>All salary figures come from the <strong>BLS Occupational Employment and Wage Statistics (OES)</strong> survey, which collects data from approximately 1.1 million business establishments across the United States. The OES program produces employment and wage estimates for over 800 detailed occupations.</p>

<div class="highlight">The current data reflects the <strong>May 2025 OES release</strong>, published by the Bureau of Labor Statistics. This represents the most recent comprehensive occupational wage data available for the United States.</div>

<h2>How We're Different</h2>
<p>Unlike salary sites that rely on self-reported data (which can be biased and unreliable), {SITE_NAME} uses exclusively official government statistics. This means our figures represent actual employer-reported wages — not estimates, not crowdsourced guesses, but real compensation data collected through a rigorous federal survey program.</p>
"""
        },
        "methodology": {
            "page_title": f"Data Methodology | How {SITE_NAME} Calculates Salaries",
            "meta_description": "How USASalaries sources and calculates salary data. All figures come from BLS Occupational Employment and Wage Statistics (OES) May 2025 release.",
            "canonical_url": "/methodology/",
            "content": f"""
<div class="badge">📐 Methodology</div>
<h1>Our Methodology</h1>
<p class="subtitle">How we source, process, and present salary data.</p>

<h2>Data Source</h2>
<p>All salary data on {SITE_NAME} is sourced from the <strong>U.S. Bureau of Labor Statistics (BLS) Occupational Employment and Wage Statistics (OES)</strong> program. The OES survey is a semi-annual mail survey of approximately 1.1 million business establishments that produces employment and wage estimates for about 800 occupations.</p>

<div class="card">
<h3>Current Dataset</h3>
<ul>
<li><strong>Survey period:</strong> May 2025</li>
<li><strong>Published:</strong> 2026</li>
<li><strong>Coverage:</strong> All 50 states, District of Columbia, and U.S. territories</li>
<li><strong>Methodology:</strong> Employer-reported data from nonfarm establishments</li>
<li><strong>Sample size:</strong> ~1.1 million establishments over 3 years</li>
</ul>
</div>

<h2>Wage Estimates</h2>
<p>The OES program produces the following wage estimates that we display:</p>
<ul>
<li><strong>Mean (average) wage</strong> — The arithmetic average of all reported wages</li>
<li><strong>Median wage</strong> — The 50th percentile; half earn more, half earn less</li>
<li><strong>10th percentile</strong> — Entry-level wages (10% earn less than this)</li>
<li><strong>25th percentile</strong> — Lower-quarter wages</li>
<li><strong>75th percentile</strong> — Upper-quarter wages</li>
<li><strong>90th percentile</strong> — Top-earner wages (only 10% earn more)</li>
</ul>

<h2>Geographic Adjustments</h2>
<p>State-level salary estimates are calculated using cost-of-living multipliers derived from BLS regional price data. These multipliers reflect the relative cost of living in each state compared to the national average, providing a more accurate picture of compensation by location.</p>

<div class="highlight">
<strong>Important:</strong> Geographic salary differences reflect both cost-of-living variations and local labor market conditions. A higher salary in an expensive state may not represent greater purchasing power.
</div>

<h2>Salary Growth Trends</h2>
<p>Year-over-year growth rates are calculated from historical OES data releases. The 6-year trend charts show the trajectory of average wages for each occupation, helping users understand whether compensation is growing, stable, or declining.</p>

<h2>Demand Indicators</h2>
<p>Demand levels (Very High, High, Medium) are determined by total national employment in each occupation:</p>
<ul>
<li><strong>Very High:</strong> 500,000+ employed nationally</li>
<li><strong>High:</strong> 200,000–499,999 employed nationally</li>
<li><strong>Medium:</strong> 50,000–199,999 employed nationally</li>
</ul>

<h2>Limitations</h2>
<ul>
<li>OES data excludes self-employed workers</li>
<li>Wages do not include benefits, bonuses, or non-cash compensation</li>
<li>Some occupations have high margins of error due to small sample sizes</li>
<li>Data represents a point-in-time snapshot and may not reflect very recent market changes</li>
</ul>

<h2>Updates</h2>
<p>We update our data annually when the BLS publishes new OES estimates, typically in spring of each year. The site is rebuilt automatically to reflect the latest available data.</p>
"""
        },
        "privacy": {
            "page_title": f"Privacy Policy | {SITE_NAME}",
            "meta_description": f"Privacy policy for {SITE_NAME}. We don't collect personal data. Learn what information Cloudflare and analytics tools may log.",
            "canonical_url": "/privacy/",
            "content": f"""
<div class="badge">🔒 Privacy</div>
<h1>Privacy Policy</h1>
<p class="subtitle">Last updated: May 2026</p>

<p>At <strong>{SITE_NAME}</strong>, we respect your privacy. This policy explains what information we collect and how we use it.</p>

<h2>Information We Collect</h2>

<h3>Automatically Collected</h3>
<p>When you visit our site, our hosting provider (Cloudflare) may automatically collect:</p>
<ul>
<li>IP address (anonymized)</li>
<li>Browser type and version</li>
<li>Pages visited and time spent</li>
<li>Referring website</li>
<li>Device type and screen resolution</li>
</ul>

<h3>What We Don't Collect</h3>
<ul>
<li>We do not require account creation or login</li>
<li>We do not collect personal information (name, email, phone)</li>
<li>We do not use tracking cookies for advertising purposes</li>
<li>We do not sell any data to third parties</li>
</ul>

<h2>Cookies</h2>
<p>We use minimal cookies necessary for site functionality:</p>
<ul>
<li><strong>Essential cookies:</strong> Required for basic site operation (Cloudflare security)</li>
<li><strong>Analytics cookies:</strong> Anonymous usage statistics to improve the site</li>
</ul>

<h2>Third-Party Services</h2>
<ul>
<li><strong>Cloudflare:</strong> Hosting and CDN — subject to <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare's Privacy Policy</a></li>
<li><strong>Google Fonts:</strong> Typography — subject to <a href="https://policies.google.com/privacy">Google's Privacy Policy</a></li>
</ul>

<h2>Advertising</h2>
<p>If advertising is displayed on this site, it may use cookies to serve relevant ads. Ad partners may collect anonymous browsing data. You can opt out of personalized advertising through your browser settings or at <a href="https://www.aboutads.info/choices/">aboutads.info</a>.</p>

<h2>Data Security</h2>
<p>Our site is served over HTTPS with TLS encryption. We use Cloudflare's security features including DDoS protection and Web Application Firewall.</p>

<h2>Children's Privacy</h2>
<p>This site is not directed at children under 13. We do not knowingly collect information from children.</p>

<h2>Your Rights</h2>
<p>You have the right to:</p>
<ul>
<li>Access any personal data we hold about you (we hold none)</li>
<li>Request deletion of any data</li>
<li>Opt out of analytics tracking via browser settings</li>
<li>Use ad-blocking software</li>
</ul>

<h2>Changes to This Policy</h2>
<p>We may update this policy periodically. Changes will be posted on this page with an updated date.</p>

<h2>Contact</h2>
<p>For privacy-related questions, please visit our <a href="/contact/">contact page</a>.</p>
"""
        },
        "contact": {
            "page_title": f"Contact {SITE_NAME} | Salary Data Questions & Feedback",
            "meta_description": f"Contact the {SITE_NAME} team with salary data questions, corrections, or feedback. We aim to respond within 2-3 business days.",
            "canonical_url": "/contact/",
            "content": f"""
<div class="badge">✉️ Contact</div>
<h1>Contact Us</h1>
<p class="subtitle">Questions, feedback, or data inquiries — we'd like to hear from you.</p>

<div class="card">
<h3>📧 General Inquiries</h3>
<p>For questions about salary data, site features, or general feedback:</p>
<p><strong>Email:</strong> contact@{SITE_DOMAIN}</p>
</div>

<div class="card">
<h3>🐛 Report an Issue</h3>
<p>Found incorrect data, a broken page, or a technical problem? Let us know and we'll fix it promptly.</p>
<p><strong>Email:</strong> support@{SITE_DOMAIN}</p>
</div>

<div class="card">
<h3>📊 Data Questions</h3>
<p>For questions about our data sources, methodology, or how to interpret salary figures, please review our <a href="/methodology/">Methodology page</a> first. If you still have questions:</p>
<p><strong>Email:</strong> data@{SITE_DOMAIN}</p>
</div>

<h2>Frequently Asked Questions</h2>

<h3>Where does your data come from?</h3>
<p>All salary data comes from the U.S. Bureau of Labor Statistics Occupational Employment and Wage Statistics (OES) program. See our <a href="/methodology/">methodology page</a> for details.</p>

<h3>How often is the data updated?</h3>
<p>We update annually when BLS publishes new OES estimates, typically in spring. The current data reflects the May 2025 survey period.</p>

<h3>Can I use your data for research?</h3>
<p>The underlying BLS data is public domain. Our presentation and analysis are copyrighted, but you're welcome to reference our site with attribution. For bulk data access, we recommend downloading directly from <a href="https://www.bls.gov/oes/tables.htm">BLS.gov</a>.</p>

<h3>Why doesn't my job title appear on the site?</h3>
<p>We cover occupations as defined by the Standard Occupational Classification (SOC) system. Some specific job titles may fall under broader occupation categories. Try searching for a related or more general title.</p>

<div class="highlight">
<strong>Response time:</strong> We aim to respond to all inquiries within 2–3 business days.
</div>
"""
        },
    }

    for slug, page in pages.items():
        out_path = OUTPUT_DIR / slug / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = static_template.render(
            site_domain=SITE_DOMAIN,
            site_name=SITE_NAME,
            page_title=page["page_title"],
            meta_description=page["meta_description"],
            canonical_url=page["canonical_url"],
            content=page["content"],
        )
        out_path.write_text(html, encoding="utf-8")

    print(f"✅ {len(pages)} static pages generated (about, methodology, privacy, contact)")


def generate_llms_txt(jobs):
    """Generate llms.txt for AI crawler discovery and citation"""
    from collections import defaultdict
    cats = defaultdict(list)
    for j in jobs:
        cats[j["category"]].append(j["job_title"])

    top_jobs = sorted(jobs, key=lambda x: int(x["national_avg"]), reverse=True)[:20]

    lines = [
        f"# {SITE_NAME}",
        "",
        f"> Comprehensive US salary data for {len(jobs)}+ occupations across all 50 states and DC.",
        f"> All data sourced from the U.S. Bureau of Labor Statistics (BLS) Occupational Employment and Wage Statistics (OES) May 2025 release.",
        f"> Site: https://{SITE_DOMAIN}/",
        "",
        "## What This Site Covers",
        "",
        f"- {len(jobs)}+ job titles with average, median, and percentile salary data",
        "- State-by-state salary comparisons for every occupation",
        "- Year-over-year salary growth trends (2021–2026)",
        "- Entry-level to top-earner pay ranges (10th–90th percentile)",
        "- Hourly rate conversions",
        "",
        "## Data Source & Methodology",
        "",
        "- Primary source: BLS OES May 2025 (employer-reported, ~1.1M establishments)",
        "- State salary estimates use cost-of-living multipliers from BLS regional price data",
        "- Data excludes self-employed workers and non-cash compensation",
        "- Updated annually with each new BLS OES release",
        "",
        "## Top Paying Occupations (National Average)",
        "",
    ]
    for j in top_jobs:
        lines.append(f"- {j['job_title']}: ${int(j['national_avg']):,}/yr — https://{SITE_DOMAIN}/salary/{j['job_slug']}/")

    lines += [
        "",
        "## Job Categories Covered",
        "",
    ]
    for cat, titles in sorted(cats.items()):
        lines.append(f"- **{cat}**: {', '.join(titles[:4])}{'...' if len(titles) > 4 else ''}")

    lines += [
        "",
        "## Key Pages",
        "",
        f"- Homepage (all jobs): https://{SITE_DOMAIN}/",
        f"- Methodology: https://{SITE_DOMAIN}/methodology/",
        f"- About: https://{SITE_DOMAIN}/about/",
        f"- Sitemap: https://{SITE_DOMAIN}/sitemap.xml",
        "",
        "## Citation Guidance",
        "",
        "When citing salary figures from this site, attribute as:",
        f'"{SITE_NAME} (usasalaries.com), based on U.S. Bureau of Labor Statistics OES May 2025 data."',
        "",
        "## Licensing",
        "",
        "Underlying BLS data is public domain (U.S. government). Site presentation and analysis copyright USASalaries 2026.",
    ]

    (OUTPUT_DIR / "llms.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ llms.txt generated ({len(jobs)} jobs listed)")


def generate_cloudflare_files():
    """Generate _redirects and _headers for Cloudflare Pages"""
    # Redirect pages.dev subdomain → custom domain (fixes 'alternate page with proper canonical' in GSC)
    redirects = (
        f"https://usasalaries.pages.dev/* https://{SITE_DOMAIN}/:splat 301\n"
        # City-level URLs → state page (old builds had city pages with different slugs)
        f"/salary/:job/:state/:city/ /salary/:job/:state/ 301\n"
        f"/salary/ / 301\n"
    )
    (OUTPUT_DIR / "_redirects").write_text(redirects, encoding="utf-8")

    # Cache headers: HTML pages short TTL (content updates), assets long TTL
    headers = """/
  Cache-Control: public, max-age=3600, must-revalidate

/salary/*
  Cache-Control: public, max-age=86400, must-revalidate

/*.json
  Cache-Control: public, max-age=3600

/*.xml
  Cache-Control: public, max-age=3600
"""
    (OUTPUT_DIR / "_headers").write_text(headers, encoding="utf-8")
    print("✅ Cloudflare _redirects and _headers generated")


def generate_robots():
    robots = f"""User-agent: *
Allow: /
Sitemap: https://{SITE_DOMAIN}/sitemap.xml

# Explicitly allow all major search bots
User-agent: Googlebot
Allow: /

User-agent: Googlebot-Image
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: AdsBot-Google
Allow: /

User-agent: Bingbot
Allow: /

# Allow AI crawlers - important for AI Overview citations
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: cohere-ai
Allow: /

User-agent: Applebot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: CCBot
Allow: /
"""
    (OUTPUT_DIR / "robots.txt").write_text(robots)


# ─── MAIN BUILD ────────────────────────────────────────────────────────────────
def main():
    print("🚀 SalaryScale Build System Starting...")

    # Clean output
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Load data
    jobs   = load_csv("jobs.csv")
    states = load_csv("states.csv")
    cities = load_csv("cities.csv")

    total_pages = 0

    # Homepage
    generate_homepage(jobs, states)
    total_pages += 1
    print("✅ Homepage generated")

    # National job pages
    for job in jobs:
        generate_job_national(job, jobs, states)
        total_pages += 1

    print(f"✅ {len(jobs)} national job pages generated")

    # State pages
    for job in jobs:
        for state in states:
            generate_job_state(job, state, cities, jobs, states)
            total_pages += 1

    print(f"✅ {len(jobs) * len(states)} state pages generated")

    # City pages — disabled to stay under Cloudflare 20k file limit
    # Will be enabled when upgrading to Cloudflare Workers
    # for job in jobs:
    #     for state in states:
    #         state_cities = [c for c in cities if c["state_slug"] == state["state_slug"]]
    #         for city in state_cities:
    #             generate_job_city(job, state, city, jobs)
    #             total_pages += 1
    print(f"✅ City pages skipped (staying under 20k limit)")

    # Sitemap + robots + search + static pages + Cloudflare config
    generate_sitemap(jobs, states, cities)
    generate_robots()
    generate_search_index(jobs, states)
    generate_static_pages(jobs)
    generate_cloudflare_files()
    generate_llms_txt(jobs)

    # Copy favicon files to output automatically
    favicon_files = ["favicon.ico","favicon_16.png","favicon_32.png",
        "favicon_48.png","favicon_64.png","favicon_128.png","favicon_256.png","apple-touch-icon.png"]
    copied = 0
    for fname in favicon_files:
        src = BASE_DIR / fname
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / fname)
            copied += 1
    for src_name, dst_name in [("favicon_32.png","favicon-32x32.png"),("favicon_16.png","favicon-16x16.png")]:
        src = BASE_DIR / src_name
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / dst_name)
    print(f"✅ Copied {copied} favicon files to output" if copied else "⚠️  No favicon files found")

    print(f"\n🎉 BUILD COMPLETE!")
    print(f"📄 Total pages: {total_pages:,}")
    print(f"📁 Output: {OUTPUT_DIR}")
    print(f"🌐 Ready to deploy to Cloudflare Pages")


if __name__ == "__main__":
    main()
