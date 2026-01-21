import requests
import json
import os
import sys
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_KEY = os.environ.get("SAM_API_KEY") 
BASE_URL = "https://api.sam.gov/opportunities/v2/search"

# EXPANDED NAICS LIST (Construction & Facilities)
NAICS_CODES = [
    "238290", # Elevators
    "236220", # Commercial Construction
    "238210", # Electrical
    "561210"  # Facilities Support
]

# REGION removed to scan ALL United States
PTYPES = ["o", "k"] 

def pull_sam_data(ptype, ncode):
    if not API_KEY:
        print("❌ Error: SAM_API_KEY is missing from GitHub Secrets.")
        return {}

    params = {
        "limit": "50", # Limit per NAICS to prevent browser crash
        "postedFrom": (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
        "postedTo": datetime.now().strftime('%m/%d/%Y'),
        "ncode": ncode,     
        # "state": REGION, <--- REMOVED to allow National search
        "ptype": ptype,
        "api_key": API_KEY
    }
    
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        if r.status_code != 200:
            print(f"⚠️ API Error {r.status_code}: {r.text}")
            return {}
        return r.json()
    except Exception as e:
        print(f"⚠️ Connection failed: {e}")
        return {}

def main():
    print(f"Starting National Scan for NAICS: {NAICS_CODES}...")
    
    all_raw_data = []
    for n in NAICS_CODES:
        for p in PTYPES:
            print(f"Scanning NAICS {n} (Type {p})...")
            data = pull_sam_data(p, n)
            all_raw_data.append(data)

    opportunities = []
    seen_ids = set()

    for data in all_raw_data:
        ops_list = data.get("opportunitiesData", [])
        if not ops_list: 
            continue

        for op in ops_list:
            key = op.get("solicitationNumber") or op.get("noticeId") or op.get("title")
            if not key or key in seen_ids:
                continue
            seen_ids.add(key)
            
            # Safe Field Extraction
            opportunities.append({
                "title": op.get("title", "Untitled Opportunity"),
                "solicitationNumber": op.get("solicitationNumber", "N/A"),
                "agency": op.get("department") or op.get("office") or "Unknown Agency",
                "postedDate": op.get("postedDate"),
                "responseDeadline": op.get("responseDeadLine") or op.get("archiveDate"),
                "link": op.get("uiLink") or "#",
                "description": op.get("description", ""),
                "setAside": op.get("typeOfSetAsideDescription", "").strip()
            })

    # Save to JSON
    with open('opportunities.json', 'w') as f:
        json.dump(opportunities, f)
    
    print(f"✅ Success: Saved {len(opportunities)} active opportunities across the US.")

if __name__ == "__main__":
    main()
