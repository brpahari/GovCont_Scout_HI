import requests
import json
import os
import sys
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
API_KEY = os.environ.get("SAM_API_KEY") 
BASE_URL = "https://api.sam.gov/opportunities/v2/search"

# SWITCH TO KEYWORDS (Catches way more than NAICS)
KEYWORDS = ["Construction", "Elevator", "Electrical", "Repair"]

# LOOK BACK 90 DAYS (Guarantees volume)
DAYS_BACK = 90
PTYPES = ["o", "k"] 

def pull_sam_data(ptype, keyword):
    if not API_KEY:
        print("❌ Error: SAM_API_KEY is missing.")
        return {}

    params = {
        "limit": "100", 
        "postedFrom": (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%m/%d/%Y'),
        "postedTo": datetime.now().strftime('%m/%d/%Y'),
        "keywords": keyword,   # <--- SEARCHING BY TEXT NOW
        "ptype": ptype,
        "api_key": API_KEY
    }
    
    try:
        r = requests.get(BASE_URL, params=params, timeout=120)
        if r.status_code != 200:
            print(f"⚠️ API Error {r.status_code}: {r.text}")
            return {}
        return r.json()
    except Exception as e:
        print(f"⚠️ Connection failed: {e}")
        return {}

def main():
    print(f"🔎 Starting Keyword Scan: {KEYWORDS}...")
    
    opportunities = []
    seen_ids = set()

    for k in KEYWORDS:
        for p in PTYPES:
            print(f"Scanning for '{k}' (Type {p})...")
            data = pull_sam_data(p, k)
            
            ops_list = data.get("opportunitiesData", [])
            print(f"   > Found {len(ops_list)} matches.")
            
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
            time.sleep(1)

    print(f"💾 Saving {len(opportunities)} opportunities to file...")
    with open('opportunities.json', 'w') as f:
        json.dump(opportunities, f)
    
    print("✅ Done.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: {e}")
        with open('opportunities.json', 'w') as f:
            json.dump([], f)
        sys.exit(1)
