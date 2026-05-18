# SalaryScale — Programmatic SEO Salary Site

Automated salary data site generating 800–250,000+ pages from BLS data.
Designed for Google AdSense monetization with AI-resistant content.

---

## Quick Start (Local Build)

```bash
# 1. Install Python dependency
pip install jinja2

# 2. Run build (generates all pages into /output)
python build.py

# 3. Preview locally
cd output && python -m http.server 8000
# Open: http://localhost:8000
```

---

## Deployment to Cloudflare Pages

### One-Time Setup

1. Push this repo to GitHub
2. Go to [Cloudflare Pages](https://pages.cloudflare.com)
3. Connect your GitHub repo
4. Set build settings:
   - **Build command:** `pip install jinja2 && python build.py`
   - **Build output directory:** `output`
5. Add GitHub Secrets (for auto-deploy):
   - `CLOUDFLARE_API_TOKEN` — from Cloudflare dashboard → API Tokens
   - `CLOUDFLARE_ACCOUNT_ID` — from Cloudflare dashboard → right sidebar

### After Setup
Every `git push` to `main` triggers automatic rebuild and deploy.
Monthly cron job auto-refreshes on the 1st of each month.

---

## Configuration

Edit top of `build.py`:

```python
SITE_DOMAIN = "yourdomain.com"        # Your domain
SITE_NAME   = "YourSiteName"          # Site brand name
ADSENSE_ID  = "ca-pub-XXXXXXXXXXXXXXX" # Google AdSense publisher ID
AD_SLOT_TOP    = "1234567890"          # AdSense ad unit slot IDs
AD_SLOT_MID    = "2345678901"
AD_SLOT_BOTTOM = "3456789012"
AD_SLOT_SIDEBAR  = "4567890123"
AD_SLOT_SIDEBAR2 = "5678901234"
```

---

## Scaling Up (250,000+ Pages)

The current dataset uses sample data (20 jobs × 20 states × 20 cities = 800 pages).
To scale to 250,000+ pages:

### Step 1: Expand Jobs (800+ job titles)
Download full BLS OES data:
- URL: https://www.bls.gov/oes/tables.htm
- Download: National industry-specific OES estimates
- Format matches `data/jobs.csv` structure

### Step 2: All 50 States
Add all 50 states to `data/states.csv`
(Current sample: 20 states)

### Step 3: Top 1,000 Cities
Add top 1,000 US cities to `data/cities.csv`
(Current sample: 20 cities)

### Projected page count with full data:
```
800 jobs × 50 states          = 40,000 state pages
800 jobs × 1,000 cities        = 800,000 city pages
800 jobs (national)            = 800 national pages
Total                          ≈ 840,000 pages
```

---

## SEO Features Built-In

| Feature | Implementation |
|---|---|
| Unique title tags | Auto-generated per page |
| Meta descriptions | Unique per page with salary data |
| Schema markup | Dataset + FAQ + Breadcrumb |
| Canonical URLs | Every page |
| Internal linking | Automatic silo structure |
| Sitemap | Auto-generated, split if >49k URLs |
| robots.txt | Configured |
| Breadcrumbs | HTML + Schema |
| FAQ sections | 4-5 PAA-targeting questions per page |
| Page speed | Static HTML, sub-200ms on Cloudflare CDN |

---

## AdSense Placement

Each page has **4 ad slots**:
1. Top banner (after hero)
2. Mid-content (after trend chart)
3. Bottom banner (after FAQ)
4. Sidebar (desktop only, 2 slots)

Apply for AdSense at: https://www.google.com/adsense
Minimum requirement: ~20-30 pages of quality content before applying.
Better threshold: Wait until 50+ pages indexed and some organic traffic.

---

## Income Projections

| Monthly Traffic | RPM | Monthly Revenue |
|---|---|---|
| 10,000 | $8 | $80 |
| 50,000 | $10 | $500 |
| 200,000 | $12 | $2,400 |
| 500,000 | $15 | $7,500 |
| 1,000,000 | $18 | $18,000 |

*RPM = Revenue per 1,000 pageviews. US salary niche typically $8-20 RPM.*

Upgrade path:
- < 10k sessions/mo: Google AdSense
- 10k+ sessions/mo: Ezoic (higher RPM)
- 50k+ sessions/mo: Mediavine (~$25+ RPM)

---

## File Structure

```
salaryscale/
├── data/
│   ├── jobs.csv          ← Job titles + BLS salary data
│   ├── states.csv        ← US states + COL multipliers
│   └── cities.csv        ← US cities + COL multipliers
├── templates/
│   └── base.html         ← Master HTML template
├── .github/
│   └── workflows/
│       └── deploy.yml    ← Auto-deploy CI/CD
├── build.py              ← Main generator script
├── output/               ← Generated site (deploy this)
└── README.md
```
