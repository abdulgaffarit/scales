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
        "temporalCoverage": "2026",
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

    # Top states by salary
    top_states_rows = []
    for s in states[:10]:
        s_salary = calc_salary(avg, s["col_multiplier"])
        diff_pct  = round((s_salary - avg) / avg * 100, 1)
        top_states_rows.append({
            "name": s["state_name"],
            "url": f"/salary/{job['job_slug']}/{s['state_slug']}/",
            "salary_fmt": fmt(s_salary),
            "diff_pct": abs(diff_pct),
            "diff_positive": diff_pct >= 0,
            "demand": job["demand"],
            "demand_class": demand_badge(job["demand"]),
        })

    # Related jobs (same category or nearby)
    related = [j for j in all_jobs if j["job_slug"] != job["job_slug"]][:8]
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
        "page_title": f"{title} Salary in 2026 | Average Pay & Hourly Rate | {SITE_NAME}",
        "meta_description": f"The average {title} salary is ${fmt(avg)}/year in 2026. See salaries by state, city, percentile, and career level. Data updated from BLS.",
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
        "comparison_rows": top_states_rows,
        "insight_title": f"What Factors Affect {title} Salary?",
        "insight_p1": f"A {title}'s salary is influenced by several key factors including geographic location, years of experience, employer type, and educational background. States with higher costs of living — such as California, New York, and Washington — typically offer 20–40% higher salaries than the national average to compensate for living expenses.",
        "insight_p2": f"Experience plays a major role in compensation. Entry-level {title}s typically earn ${fmt(pct['p10'])}–${fmt(pct['p25'])} per year, while senior professionals with 10+ years of experience can command ${fmt(pct['p75'])}–${fmt(pct['p90'])} annually. Specialization and advanced certifications can further boost earning potential.",
        "insight_p3": f"Employer size also matters. Large corporations and government agencies tend to offer more competitive packages including benefits, retirement plans, and bonuses. The {title} role currently has {job['demand'].lower()} demand in the job market with a {job['yoy_growth']}% growth rate, making it one of the {'most' if float(job['yoy_growth']) > 4 else 'steadily'} growing careers in the {job['category']} sector.",
        "related_jobs": related_jobs,
        "faqs": faqs,
        "schema_json": dataset_schema(f"{title} Salary 2026", f"Comprehensive salary data for {title} professionals in the United States.", url),
        "breadcrumb_schema": breadcrumb_schema([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": url}]),
        "breadcrumb_html": breadcrumb_html([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": url}]),
        "top_states": sidebar_states,
        "top_cities": [],
        "category_jobs": category_jobs,
        "related_links": [{"url": f"/salary/{job['job_slug']}/{s['state_slug']}/", "text": f"{title} Salary in {s['state_name']}"} for s in states[:8]],
    })
    write_page(f"salary/{job['job_slug']}", ctx)


def generate_job_state(job, state, all_cities, all_jobs):
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
            "url": f"/salary/{job['job_slug']}/{state['state_slug']}/{c['city_slug']}/",
            "salary_fmt": fmt(c_salary),
            "diff_pct": abs(diff_pct),
            "diff_positive": diff_pct >= 0,
            "demand": job["demand"],
            "demand_class": demand_badge(job["demand"]),
        })

    # Top cities for sidebar
    top_cities_sidebar = sorted(state_cities, key=lambda c: float(c["col_multiplier"]), reverse=True)[:5]
    sidebar_cities = [{"name": c["city_name"], "url": f"/salary/{job['job_slug']}/{state['state_slug']}/{c['city_slug']}/", "salary_fmt": fmt(calc_salary(avg, c["col_multiplier"]))} for c in top_cities_sidebar]

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
        "page_title": f"{title} Salary in {sname} (2026) | ${fmt(avg)}/yr | {SITE_NAME}",
        "meta_description": f"Average {title} salary in {sname} is ${fmt(avg)}/year in 2026. See city-by-city breakdown, trend data, and how {sname} compares to other states.",
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
        "breadcrumb_schema": breadcrumb_schema([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": url}]),
        "breadcrumb_html": breadcrumb_html([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": url}]),
        "top_states": [],
        "top_cities": sidebar_cities,
        "category_jobs": [],
        "related_links": [{"url": f"/salary/{job['job_slug']}/{state['state_slug']}/{c['city_slug']}/", "text": f"{title} Salary in {c['city_name']}"} for c in state_cities[:8]],
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
        "page_title": f"{title} Salary in {cname}, {sname} (2026) | ${fmt(avg)}/yr | {SITE_NAME}",
        "meta_description": f"Average {title} salary in {cname}, {sname} is ${fmt(avg)}/year. Compare hourly rates, percentiles, and see how {cname} stacks up vs other cities.",
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
        "breadcrumb_schema": breadcrumb_schema([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": f"/salary/{job['job_slug']}/{state['state_slug']}/"}, {"name": cname, "url": url}]),
        "breadcrumb_html": breadcrumb_html([{"name": "Salaries", "url": "/salary/"}, {"name": f"{title} Salary", "url": f"/salary/{job['job_slug']}/"}, {"name": sname, "url": f"/salary/{job['job_slug']}/{state['state_slug']}/"}, {"name": cname, "url": url}]),
        "top_states": [],
        "top_cities": [],
        "category_jobs": [],
        "related_links": [{"url": f"/salary/{r['job_slug']}/{state['state_slug']}/{city['city_slug']}/", "text": f"{r['job_title']} Salary in {cname}"} for r in [j for j in all_jobs if j['job_slug'] != job['job_slug']][:8]],
    })
    write_page(f"salary/{job['job_slug']}/{state['state_slug']}/{city['city_slug']}", ctx)


def generate_homepage(jobs, states):
    """Generate homepage"""
    out_path = OUTPUT_DIR / "index.html"
    top_jobs = jobs[:12]
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>US Salary Data 2026 — Every Job, Every State, Every City | {SITE_NAME}</title>
  <meta name="description" content="Find accurate 2026 salary data for any job in any US state or city. Data sourced from BLS. Compare salaries, see trends, and make informed career decisions.">
  <link rel="canonical" href="https://{SITE_DOMAIN}/">
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{ --primary: #1a56db; --accent: #16a34a; --bg: #f8fafc; --card: #fff; --text: #1e293b; --muted: #64748b; --border: #e2e8f0; --radius: 10px; --max: 1100px; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ background: #fff; border-bottom: 1px solid var(--border); padding: 0 20px; }}
    .header-inner {{ max-width: var(--max); margin: 0 auto; height: 60px; display: flex; align-items: center; justify-content: space-between; }}
    .logo {{ font-size: 1.4rem; font-weight: 800; color: var(--primary); text-decoration: none; }}
    .logo span {{ color: var(--accent); }}
    .hero {{ background: linear-gradient(135deg, #1a56db, #1240a8); color: white; padding: 70px 20px; text-align: center; }}
    .hero h1 {{ font-size: 2.5rem; font-weight: 900; margin-bottom: 15px; }}
    .hero p {{ opacity: 0.85; font-size: 1.1rem; max-width: 600px; margin: 0 auto 30px; }}
    .search-bar {{ display: flex; max-width: 500px; margin: 0 auto; background: white; border-radius: 50px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }}
    .search-bar input {{ flex: 1; border: none; padding: 15px 20px; font-size: 1rem; outline: none; color: var(--text); }}
    .search-bar button {{ background: var(--accent); color: white; border: none; padding: 15px 25px; font-weight: 700; cursor: pointer; font-size: 0.95rem; }}
    .container {{ max-width: var(--max); margin: 0 auto; padding: 50px 20px; }}
    .section-title {{ font-size: 1.4rem; font-weight: 800; margin-bottom: 25px; }}
    .jobs-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-bottom: 50px; }}
    .job-card {{ background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; text-decoration: none; color: var(--text); transition: all 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
    .job-card:hover {{ border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(26,86,219,0.15); }}
    .job-card .j-title {{ font-weight: 700; margin-bottom: 5px; }}
    .job-card .j-salary {{ color: var(--primary); font-size: 1.1rem; font-weight: 800; }}
    .job-card .j-cat {{ font-size: 0.78rem; color: var(--muted); margin-top: 4px; }}
    footer {{ background: #1e293b; color: #94a3b8; padding: 40px 20px; text-align: center; font-size: 0.85rem; }}
  </style>
</head>
<body>
<header>
  <div class="header-inner">
    <a href="/" class="logo">USA <span>Salaries</span></a>
  </div>
</header>
<div class="hero">
  <h1>2026 USA Salary Guide</h1>
  <p>Accurate salary data for every job, state, and city in America. Updated from BLS official data.</p>
</div>
<div class="container">
  <div class="section-title">Browse Salaries by Job Title</div>
  <div class="jobs-grid">
    {"".join(f'<a href="/salary/{j["job_slug"]}/" class="job-card"><div class="j-title">{j["job_title"]}</div><div class="j-salary">${fmt(int(j["national_avg"]))}/yr</div><div class="j-cat">{j["category"]}</div></a>' for j in jobs)}
  </div>
</div>
<footer>© 2026 {SITE_NAME} · Data from U.S. Bureau of Labor Statistics</footer>
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")


# ─── SITEMAP GENERATOR ─────────────────────────────────────────────────────────
def generate_sitemap(jobs, states, cities):
    urls = [f"https://{SITE_DOMAIN}/"]
    for j in jobs:
        urls.append(f"https://{SITE_DOMAIN}/salary/{j['job_slug']}/")
        for s in states:
            urls.append(f"https://{SITE_DOMAIN}/salary/{j['job_slug']}/{s['state_slug']}/")
            state_cities = [c for c in cities if c["state_slug"] == s["state_slug"]]
            for c in state_cities:
                urls.append(f"https://{SITE_DOMAIN}/salary/{j['job_slug']}/{s['state_slug']}/{c['city_slug']}/")

    # Split into sitemap index if > 50k URLs
    chunk_size = 49000
    chunks = [urls[i:i+chunk_size] for i in range(0, len(urls), chunk_size)]

    for idx, chunk in enumerate(chunks):
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for url in chunk:
            sm += f"  <url><loc>{url}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>\n"
        sm += "</urlset>"
        fname = f"sitemap-{idx+1}.xml" if len(chunks) > 1 else "sitemap.xml"
        (OUTPUT_DIR / fname).write_text(sm, encoding="utf-8")

    if len(chunks) > 1:
        index = '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for i in range(len(chunks)):
            index += f"  <sitemap><loc>https://{SITE_DOMAIN}/sitemap-{i+1}.xml</loc></sitemap>\n"
        index += "</sitemapindex>"
        (OUTPUT_DIR / "sitemap.xml").write_text(index, encoding="utf-8")

    print(f"✅ Sitemap: {len(urls):,} URLs across {len(chunks)} file(s)")


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
            generate_job_state(job, state, cities, jobs)
            total_pages += 1

    print(f"✅ {len(jobs) * len(states)} state pages generated")

    # City pages
    for job in jobs:
        for state in states:
            state_cities = [c for c in cities if c["state_slug"] == state["state_slug"]]
            for city in state_cities:
                generate_job_city(job, state, city, jobs)
                total_pages += 1

    print(f"✅ City pages generated")

    # Sitemap + robots
    generate_sitemap(jobs, states, cities)
    generate_robots()

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
