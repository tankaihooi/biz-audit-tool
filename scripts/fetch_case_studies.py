"""One-off scraper: pull Power Platform case studies as raw markdown into data/raw/.

Source: https://learn.microsoft.com/en-us/power-platform/guidance/case-studies/
The docs site is generated from public markdown, so we fetch that directly
instead of scraping rendered HTML.

Usage: python -m scripts.fetch_case_studies
"""

import time
from pathlib import Path

import requests

RAW_BASE = (
    "https://raw.githubusercontent.com/MicrosoftDocs/power-platform/main/"
    "power-platform/guidance/case-studies/{slug}.md"
)

# Slugs from the case-studies index page (learn.microsoft.com/.../case-studies/)
SLUGS = [
    "boost-efficiency-experience-case-study",
    "abn-amro-enhances-ai",
    "action-apps-athlete-management",
    "aecom-streamlined-onboarding",
    "automate-business-processes",
    "city-montreal-citizen-engagement",
    "concentrix-invoice-processing",
    "daimler-truck-modernizes-policies",
    "nonprofit",
    "db-empowers-citizen-devs",
    "dunaway-streamlines-city-code-research",
    "streamline-employee-onboarding",
    "global-finance",
    "grupo-bimbo-global-audit",
    "holland-america-customer-experience",
    "engineering-time-tracking",
    "latrobe-supercharges",
    "lloyds-banking-group",
    "mobilezone-modernizes-service-delivery",
    "nexi-revolutionizes-customer-support",
    "rabobank-conversational-banking",
    "signetic-transforms-healthcare",
    "scdf-implements-digital-solutions",
    "slb-enhances-productivity",
    "teck-automates-data-extraction",
    "tiendas-cuadra-customer-service",
    "tmobile-empowers-customer-service",
]

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch_all() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []

    for slug in SLUGS:
        url = RAW_BASE.format(slug=slug)
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"  FAIL ({resp.status_code}) {slug}")
            failed.append(slug)
            time.sleep(0.2)
            continue

        (OUT_DIR / f"{slug}.md").write_text(resp.text, encoding="utf-8")
        print(f"  OK   {slug}")
        ok += 1
        time.sleep(0.2)

    print(f"\nFetched {ok}/{len(SLUGS)} case studies into {OUT_DIR}")
    if failed:
        print(f"Failed slugs (check URL/slug on the index page): {failed}")


if __name__ == "__main__":
    fetch_all()
