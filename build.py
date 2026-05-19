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
    """Generate modern homepage"""
    out_path = OUTPUT_DIR / "index.html"

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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>US Salary Data 2026 by Job, State &amp; City | {SITE_NAME}</title>
  <meta name="description" content="Explore 2026 US salary data for {len(jobs)}+ jobs across every state and major city. Compare pay by location, career level, and industry using BLS data.">
  <link rel="canonical" href="https://{SITE_DOMAIN}/">
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <meta name="theme-color" content="#2563eb">
  <script type="application/ld+json">{{
    "@context":"https://schema.org",
    "@type":"WebSite",
    "name":"{SITE_NAME}",
    "url":"https://{SITE_DOMAIN}",
    "description":"Comprehensive US salary data for {len(jobs)}+ occupations across all 50 states.",
    "potentialAction":{{"@type":"SearchAction","target":"https://{SITE_DOMAIN}/salary/{{search_term_string}}/","query-input":"required name=search_term_string"}}
  }}</script>
  <style>
:root{{--blue:#2563eb;--blue-d:#1d4ed8;--blue-50:#eff6ff;--blue-100:#dbeafe;--green:#16a34a;--green-50:#f0fdf4;--gray-900:#111827;--gray-700:#374151;--gray-600:#4b5563;--gray-500:#6b7280;--gray-300:#d1d5db;--gray-200:#e5e7eb;--gray-100:#f3f4f6;--gray-50:#f9fafb;--white:#fff;--shadow:0 1px 3px rgba(0,0,0,.1),0 1px 2px rgba(0,0,0,.06);--shadow-md:0 4px 6px rgba(0,0,0,.07);--radius:10px;--radius-lg:16px;--max:1140px;--tr:0.18s ease;--font:'Inter','Segoe UI',system-ui,sans-serif}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--font);background:var(--gray-50);color:var(--gray-900);-webkit-font-smoothing:antialiased}}
a{{color:var(--blue);text-decoration:none}}
a:hover{{text-decoration:underline}}

/* HEADER */
.site-header{{background:var(--white);border-bottom:1px solid var(--gray-200);position:sticky;top:0;z-index:200;box-shadow:0 1px 2px rgba(0,0,0,.05)}}
.header-inner{{max-width:var(--max);margin:0 auto;padding:0 24px;height:62px;display:flex;align-items:center;gap:20px}}
.logo{{font-size:1.2rem;font-weight:800;color:var(--blue);text-decoration:none;white-space:nowrap;flex-shrink:0}}
.logo span{{color:var(--green)}}
.header-search{{flex:1;max-width:400px;position:relative}}
.header-search input{{width:100%;padding:8px 14px 8px 36px;border:1.5px solid var(--gray-200);border-radius:50px;font-size:0.875rem;color:var(--gray-900);background:var(--gray-50);outline:none;transition:all var(--tr)}}
.header-search input:focus{{border-color:var(--blue);background:var(--white);box-shadow:0 0 0 3px var(--blue-100)}}
.search-icon{{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--gray-400);width:15px;height:15px;pointer-events:none}}
.header-nav{{display:flex;align-items:center;gap:2px;margin-left:auto}}
.header-nav a{{color:var(--gray-600);font-size:0.85rem;font-weight:500;padding:6px 11px;border-radius:6px;transition:all var(--tr);white-space:nowrap}}
.header-nav a:hover{{color:var(--blue);background:var(--blue-50);text-decoration:none}}

/* HERO */
.hero{{background:linear-gradient(135deg,var(--blue) 0%,var(--blue-d) 100%);color:var(--white);padding:60px 24px 50px;text-align:center;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;left:-100px;top:-100px;width:400px;height:400px;border-radius:50%;background:rgba(255,255,255,.04);pointer-events:none}}
.hero::after{{content:'';position:absolute;right:-80px;bottom:-80px;width:300px;height:300px;border-radius:50%;background:rgba(255,255,255,.04);pointer-events:none}}
.hero-inner{{max-width:720px;margin:0 auto;position:relative;z-index:1}}
.hero-label{{display:inline-block;background:rgba(255,255,255,.15);border-radius:50px;padding:4px 14px;font-size:0.75rem;font-weight:600;letter-spacing:.4px;margin-bottom:18px}}
.hero h1{{font-size:2.6rem;font-weight:900;line-height:1.2;margin-bottom:14px;letter-spacing:-.5px}}
.hero-desc{{font-size:1.05rem;opacity:.85;margin-bottom:30px;line-height:1.6}}
.hero-search{{display:flex;max-width:540px;margin:0 auto 24px;background:var(--white);border-radius:50px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.2)}}
.hero-search input{{flex:1;border:none;padding:15px 20px;font-size:0.975rem;outline:none;color:var(--gray-900)}}
.hero-search button{{background:var(--green);color:var(--white);border:none;padding:15px 24px;font-weight:700;cursor:pointer;font-size:0.9rem;white-space:nowrap;transition:background var(--tr)}}
.hero-search button:hover{{background:#15803d}}
.hero-stats{{display:flex;justify-content:center;gap:32px;flex-wrap:wrap}}
.hero-stat{{text-align:center}}
.hero-stat-num{{font-size:1.6rem;font-weight:900}}
.hero-stat-label{{font-size:0.75rem;opacity:.75;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}

/* MAIN LAYOUT */
.main-wrap{{max-width:var(--max);margin:0 auto;padding:32px 24px 60px;display:grid;grid-template-columns:1fr 280px;gap:28px;align-items:start}}

/* CATEGORY NAV */
.cat-nav{{background:var(--white);border:1px solid var(--gray-200);border-radius:var(--radius-lg);padding:16px 18px;margin-bottom:24px;box-shadow:var(--shadow)}}
.cat-nav-label{{font-size:0.76rem;font-weight:600;color:var(--gray-500);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}}
.cat-pills{{display:flex;flex-wrap:wrap;gap:7px}}
.cat-pills a{{padding:5px 13px;border-radius:50px;text-decoration:none;font-size:0.8rem;font-weight:500;background:var(--gray-100);color:var(--gray-700);border:1px solid var(--gray-200);transition:all var(--tr)}}
.cat-pills a:hover{{background:var(--blue);color:var(--white);border-color:var(--blue);text-decoration:none}}

/* CATEGORY SECTION */
.cat-section{{margin-bottom:36px}}
.cat-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--gray-200)}}
.cat-icon{{font-size:1.3rem}}
.cat-name{{font-size:1.05rem;font-weight:800;color:var(--gray-900)}}
.cat-count{{margin-left:auto;font-size:0.76rem;color:var(--gray-500);background:var(--gray-100);padding:3px 9px;border-radius:50px}}
.cat-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}}

/* JOB TILE */
.job-tile{{background:var(--white);border:1.5px solid var(--gray-200);border-radius:var(--radius);padding:14px;transition:all var(--tr);display:block;text-decoration:none}}
.job-tile:hover{{border-color:var(--blue);box-shadow:var(--shadow-md);transform:translateY(-1px);text-decoration:none}}
.tile-name{{font-size:0.84rem;font-weight:600;color:var(--gray-900);margin-bottom:5px;line-height:1.3}}
.tile-salary{{font-size:1rem;font-weight:800;color:var(--blue)}}
.tile-salary span{{font-size:.73rem;font-weight:500;color:var(--gray-500)}}
.tile-demand{{font-size:0.7rem;margin-top:4px;font-weight:500}}
.d-high{{color:var(--green)}}
.d-mid{{color:var(--gray-500)}}

/* SIDEBAR */
.hp-sidebar{{display:flex;flex-direction:column;gap:16px}}
.sidebar-card{{background:var(--white);border:1px solid var(--gray-200);border-radius:var(--radius-lg);padding:18px;box-shadow:var(--shadow)}}
.s-title{{font-size:0.85rem;font-weight:700;color:var(--gray-900);margin-bottom:12px}}
.top-job-item{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--gray-100);font-size:0.83rem}}
.top-job-item:last-child{{border-bottom:none}}
.top-job-name{{color:var(--gray-700);font-weight:500}}
.top-job-name:hover{{color:var(--blue);text-decoration:none}}
.top-job-salary{{font-weight:700;color:var(--gray-900);font-size:0.8rem}}
.trending-list{{list-style:none}}
.trending-list li{{padding:7px 0;border-bottom:1px solid var(--gray-100);font-size:0.84rem}}
.trending-list li:last-child{{border-bottom:none}}
.trending-list a{{color:var(--gray-700);font-weight:500}}
.trending-list a:hover{{color:var(--blue)}}
.trending-num{{display:inline-block;width:18px;height:18px;border-radius:50%;background:var(--blue-100);color:var(--blue);font-size:0.65rem;font-weight:700;text-align:center;line-height:18px;margin-right:6px}}

/* FOOTER */
.site-footer{{background:var(--gray-900);color:#9ca3af;padding:48px 24px 28px;margin-top:60px}}
.footer-grid{{max-width:var(--max);margin:0 auto;display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:36px;margin-bottom:36px}}
.footer-logo{{font-size:1.15rem;font-weight:800;color:var(--white);margin-bottom:9px}}
.footer-desc{{font-size:0.82rem;line-height:1.65;max-width:260px}}
.footer-col h4{{font-size:0.76rem;font-weight:700;color:#e2e8f0;text-transform:uppercase;letter-spacing:.6px;margin-bottom:12px}}
.footer-col a{{display:block;font-size:0.84rem;color:#9ca3af;margin-bottom:7px;transition:color var(--tr)}}
.footer-col a:hover{{color:var(--white);text-decoration:none}}
.footer-bottom{{max-width:var(--max);margin:0 auto;padding-top:22px;border-top:1px solid #1f2937;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;font-size:0.79rem}}
.footer-links{{display:flex;gap:18px}}
.footer-links a{{color:#6b7280}}
.footer-links a:hover{{color:#d1d5db;text-decoration:none}}

/* RESPONSIVE */
@media(max-width:960px){{.main-wrap{{grid-template-columns:1fr}}.hp-sidebar{{display:none}}.footer-grid{{grid-template-columns:1fr 1fr}}}}
@media(max-width:640px){{.header-inner{{padding:0 14px;height:54px}}.header-search{{display:none}}.header-nav a{{font-size:0.78rem;padding:5px 7px}}.hero{{padding:40px 16px 36px}}.hero h1{{font-size:1.8rem}}.hero-stats{{gap:18px}}.main-wrap{{padding:16px 12px 40px}}.cat-grid{{grid-template-columns:1fr 1fr}}.footer-grid{{grid-template-columns:1fr;gap:20px}}.footer-bottom{{flex-direction:column;text-align:center}}}}
@media(max-width:380px){{.hero h1{{font-size:1.5rem}}.cat-grid{{grid-template-columns:1fr}}.header-nav{{display:none}}}}
  </style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <a href="/" class="logo">USA<span>Salaries</span></a>
    <div class="header-search">
      <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" placeholder="Search by job title or state…" aria-label="Search">
    </div>
    <nav class="header-nav">
      <a href="/salary/">Browse</a>
      <a href="/salary/registered-nurse/">Healthcare</a>
      <a href="/salary/software-developer/">Tech</a>
      <a href="/salary/electrician/">Trades</a>
    </nav>
  </div>
</header>

<section class="hero">
  <div class="hero-inner">
    <div class="hero-label">📊 BLS Official Data · May 2025 Release</div>
    <h1>USA Salary Data 2026 for Every Job, State &amp; City</h1>
    <p class="hero-desc">Explore accurate salary data for {len(jobs)}+ occupations across all 50 states and major cities. Updated from official U.S. Bureau of Labor Statistics data.</p>
    <div class="hero-search">
      <input type="text" placeholder="Search job titles, states, or cities…" aria-label="Search salaries">
      <button type="button">Search Salaries</button>
    </div>
    <div class="hero-stats">
      <div class="hero-stat"><div class="hero-stat-num">{len(jobs)}+</div><div class="hero-stat-label">Job Titles</div></div>
      <div class="hero-stat"><div class="hero-stat-num">51</div><div class="hero-stat-label">States</div></div>
      <div class="hero-stat"><div class="hero-stat-num">18,981</div><div class="hero-stat-label">Salary Pages</div></div>
      <div class="hero-stat"><div class="hero-stat-num">2026</div><div class="hero-stat-label">Data Year</div></div>
    </div>
  </div>
</section>

<div class="main-wrap">
  <main>
    <div class="cat-nav">
      <div class="cat-nav-label">Browse by Category</div>
      <div class="cat-pills">{cat_nav}</div>
    </div>
    {cat_sections}
  </main>

  <aside class="hp-sidebar">
    <div class="sidebar-card">
      <div class="s-title">🏆 Highest Paying Jobs</div>
      {top_jobs_html}
    </div>

    <div class="sidebar-card">
      <div class="s-title">🔥 Trending Searches</div>
      <ul class="trending-list">
        {"".join(f'<li><span class="trending-num">{i+1}</span><a href="/salary/{j["job_slug"]}/">{j["job_title"]}</a></li>' for i, j in enumerate(sorted(jobs, key=lambda x: float(x["yoy_growth"]), reverse=True)[:7]))}
      </ul>
    </div>

    <div class="sidebar-card" style="background:var(--blue-50);border-color:var(--blue-100)">
      <div class="s-title" style="color:#1e40af">🏛️ About This Data</div>
      <p style="font-size:0.79rem;color:#1e40af;line-height:1.6">All salary data sourced from the U.S. Bureau of Labor Statistics Occupational Employment and Wage Statistics (OES) program. May 2025 national release.</p>
    </div>
  </aside>
</div>

<footer class="site-footer">
  <div class="footer-grid">
    <div>
      <div class="footer-logo">USASalaries</div>
      <p class="footer-desc">Salary intelligence for every job, state, and city in America. Sourced from official BLS data. Updated annually.</p>
    </div>
    <div class="footer-col">
      <h4>Top Jobs</h4>
      {"".join(f'<a href="/salary/{j["job_slug"]}/">{j["job_title"]}</a>' for j in sorted(jobs, key=lambda x: int(x["national_avg"]), reverse=True)[:6])}
    </div>
    <div class="footer-col">
      <h4>Browse by State</h4>
      {"".join(f'<a href="/salary/registered-nurse/{s["state_slug"]}/">{s["state_name"]}</a>' for s in states[:6])}
    </div>
    <div class="footer-col">
      <h4>Company</h4>
      <a href="/about/">About</a>
      <a href="/methodology/">Methodology</a>
      <a href="/privacy/">Privacy Policy</a>
      <a href="/contact/">Contact</a>
      <a href="/sitemap.xml">Sitemap</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© 2026 USASalaries · Data from U.S. Bureau of Labor Statistics · For informational purposes only.</span>
    <div class="footer-links"><a href="/privacy/">Privacy</a><a href="/methodology/">Methodology</a><a href="/sitemap.xml">Sitemap</a></div>
  </div>
</footer>
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
            # City URLs disabled — staying under Cloudflare 20k file limit
            # state_cities = [c for c in cities if c["state_slug"] == s["state_slug"]]
            # for c in state_cities:
            #     urls.append(f"https://{SITE_DOMAIN}/salary/{j['job_slug']}/{s['state_slug']}/{c['city_slug']}/")

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

    # City pages — disabled to stay under Cloudflare 20k file limit
    # Will be enabled when upgrading to Cloudflare Workers
    # for job in jobs:
    #     for state in states:
    #         state_cities = [c for c in cities if c["state_slug"] == state["state_slug"]]
    #         for city in state_cities:
    #             generate_job_city(job, state, city, jobs)
    #             total_pages += 1
    print(f"✅ City pages skipped (staying under 20k limit)")

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
