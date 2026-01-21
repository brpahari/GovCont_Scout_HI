import requests
import json
import os
import sys
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_KEY = os.environ.get("SAM_API_KEY") 
BASE_URL = "https://api.sam.gov/opportunities/v2/search"

# EXPANDED LIST
NAICS_CODES = [
    "238290", # Elevators
    "236220", # Commercial Construction
    "238210", # Electrical
    "561210"  # Facilities Support
]

REGION = "HI"       
PTYPES = ["o", "k"] 

def pull_sam_data(ptype, ncode):
    if not API_KEY:
        raise ValueError("CRITICAL ERROR: SAM_API_KEY is missing. Check GitHub Secrets.")

    params = {
        "limit": "100",
        "postedFrom": (datetime.now() - timedelta(days=60)).strftime('%m/%d/%Y'),
        "postedTo": datetime.now().strftime('%m/%d/%Y'),
        "ncode": ncode,     
        "state": REGION,    
        "ptype": ptype,
        "api_key": API_KEY
    }
    
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        # If API returns error, print it but don't crash
        if r.status_code != 200:
            print(f"⚠️ API Error for {ncode}/{ptype}: {r.status_code} - {r.text}")
            return {}
        return r.json()
    except Exception as e:
        print(f"⚠️ Connection failed for {ncode}/{ptype}: {e}")
        return {}

def main():
    print(f"Starting Scan for Hawaii (NAICS: {NAICS_CODES})...")
    
    all_raw_data = []
    for n in NAICS_CODES:
        for p in PTYPES:
            print(f"Scanning NAICS {n} (Type {p})...")
            data = pull_sam_data(p, n)
            all_raw_data.append(data)

    opportunities = []
    seen_ids = set()

    for data in all_raw_data:
        # Safe access to data
        ops_list = data.get("opportunitiesData", [])
        if not ops_list: 
            continue

        for op in ops_list:
            key = op.get("solicitationNumber") or op.get("noticeId") or op.get("title")
            if not key or key in seen_ids:
                continue
            seen_ids.add(key)
            
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

    # Always save the file, even if empty, to prevent "File Not Found" errors
    with open('opportunities.json', 'w') as f:
        json.dump(opportunities, f)
    
    print(f"✅ Success: Saved {len(opportunities)} opportunities.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ FATAL SCRIPT ERROR: {e}")
        sys.exit(1) # NOW we exit with error so you can see it
