import json
import os
import requests
import sys
from datetime import datetime, timedelta

# --- CONFIGURATION ---
NAICS_CODES = ["238290", "236220", "238210", "561210"]
DAYS_BACK = 1825 # 5 Years
LIMIT = 500 

OUT_TOP = "intelligence_top.json"
URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

def fetch_awards():
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"], 
            "naics_codes": {"require": NAICS_CODES},
            # REMOVED "Country" to be safe, just use State
            "place_of_performance_locations": [{"state": "HI"}] 
        },
        "fields": [
            "Award ID", "Recipient Name", "Total Obligation", 
            "Awarding Agency", "Description", "Date Signed"
        ],
        "page": 1, 
        "limit": LIMIT, 
        "sort": "Total Obligation", 
        "order": "desc"
    }

    try:
        r = requests.post(URL, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        if r.status_code != 200:
            print(f"⚠️ API Error: {r.status_code} - {r.text}")
            return [], {}
        data = r.json()
        return data.get("results", []), {"start_date": start_date, "end_date": end_date}
    except Exception as e:
        print(f"⚠️ Connection failed: {e}")
        return [], {}

def aggregate_data(rows, key_field, top_n=5):
    totals = {}
    for r in rows:
        name = r.get(key_field) or "Unknown"
        val = float(r.get("Total Obligation", 0) or 0)
        totals[name] = totals.get(name, 0.0) + val
    
    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [{"name": k, "value": v} for k, v in sorted_items]

def main():
    print(f"Fetching Intelligence for Hawaii Construction...")
    results, meta_dates = fetch_awards()

    top_competitors = aggregate_data(results, "Recipient Name", top_n=10)
    top_agencies = aggregate_data(results, "Awarding Agency", top_n=5)

    meta = {
        "naics_code": "Multiple (Const/Fac)",
        "days_back": DAYS_BACK,
        "generated_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(results)
    }

    data_out = {
        "meta": meta,
        "top_competitors": top_competitors,
        "top_agencies": top_agencies
    }

    with open(OUT_TOP, "w", encoding="utf-8") as f:
        json.dump(data_out, f, ensure_ascii=False)

    print(f"✅ Success: Processed {len(results)} awards.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ FATAL SCRIPT ERROR: {e}")
        sys.exit(1)
