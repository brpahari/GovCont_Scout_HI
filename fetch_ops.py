import requests
import json
import os
import sys
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_KEY = os.environ.get("SAM_API_KEY") 
BASE_URL = "https://api.sam.gov/opportunities/v2/search"

# NATIONAL SCOPE (No Region Filter)
NAICS_CODES = [
    "238290", # Elevators
    "236220", # Commercial Construction
    "238210", # Electrical
    "561210"  # Facilities Support
]
PTYPES = ["o", "k"] 

def pull_sam_data(ptype, ncode):
    if not API_KEY:
        print("❌ Error: SAM_API_KEY is missing.")
        return {}

    params = {
        "limit": "50", 
        "postedFrom": (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y'),
        "postedTo": datetime.now().strftime('%m/%d/%Y'),
        "ncode": ncode,     
        "ptype": ptype,
        "api_key": API_KEY
    }
    
    try:
        # INCREASED TIMEOUT TO 120 SECONDS
        r = requests.get(BASE_URL, params=params, timeout=120)
        if r.status_code != 200:
            print(f"⚠️ API Error {r.status_code} for {ncode}")
            return {}
        return r.json()
    except Exception as e:
        print(f"⚠️ Connection failed for {ncode}: {e}")
        return {}

def main():
    print(f"🇺🇸 Starting National Scan...")
    
    opportunities = []
    seen_ids = set()

    # Loop through NAICS
    for n in NAICS_CODES:
        for p in PTYPES:
            print(f"Scanning NAICS {n} (Type {p})...")
            data = pull_sam_data(p, n)
            
            # Process immediately to save memory
            ops_list = data.get("opportunitiesData", [])
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
            
            # Sleep 1s to avoid hitting API limits
            time.sleep(1)

    # SAFETY SAVE: Writes file even if 0 results found
    print(f"💾 Saving {len(opportunities)} opportunities to file...")
    with open('opportunities.json', 'w') as f:
        json.dump(opportunities, f)
    
    print("✅ Done.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: {e}")
        # Emergency Empty File Save to prevent 'Loading...' stuck state
        with open('opportunities.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)
