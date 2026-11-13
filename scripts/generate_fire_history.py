"""
Generator for NASA FIRMS VIIRS Active Fire Anomalies Historical Archive (12 Months).
Creates scientifically accurate synthetic VIIRS 375m active fire detections across the Punjab airshed
spanning the last year (Nov 2025 - Nov 2026), including Kharif & Rabi stubble burning seasons,
live active fires, and 24-hour detections.
"""
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Geographic fire cluster centroids: [name, lat, lon, region, weight]
AGRICULTURAL_FIRE_CLUSTERS = [
    # Indian Punjab (Paddy Stubble Epicenter)
    ("Amritsar", 31.63, 74.87, "Punjab (India)", 1.2),
    ("Tarn Taran", 31.45, 74.92, "Punjab (India)", 1.3),
    ("Firozpur", 30.92, 74.61, "Punjab (India)", 1.2),
    ("Fazilka", 30.40, 74.02, "Punjab (India)", 0.9),
    ("Bathinda", 30.21, 74.94, "Punjab (India)", 1.4),
    ("Sangrur", 30.24, 75.84, "Punjab (India)", 1.5),
    ("Ludhiana", 30.90, 75.85, "Punjab (India)", 1.1),
    ("Patiala", 30.34, 76.38, "Punjab (India)", 1.2),
    ("Mansa", 29.98, 75.39, "Punjab (India)", 1.0),
    ("Barnala", 30.38, 75.54, "Punjab (India)", 1.1),
    ("Jalandhar", 31.32, 75.57, "Punjab (India)", 0.8),
    ("Kapurthala", 31.38, 75.38, "Punjab (India)", 0.8),
    ("Moga", 30.81, 75.17, "Punjab (India)", 1.0),

    # Pakistani Punjab (Rice-Wheat & Sugarcane Residue Belt)
    ("Sheikhupura", 31.71, 73.98, "Punjab (Pakistan)", 1.0),
    ("Gujranwala", 32.16, 74.19, "Punjab (Pakistan)", 1.1),
    ("Hafizabad", 32.07, 73.69, "Punjab (Pakistan)", 0.9),
    ("Nankana Sahib", 31.45, 73.70, "Punjab (Pakistan)", 0.9),
    ("Kasur", 31.12, 74.44, "Punjab (Pakistan)", 1.0),
    ("Okara", 30.81, 73.45, "Punjab (Pakistan)", 0.8),
    ("Sahiwal", 30.67, 73.10, "Punjab (Pakistan)", 0.8),
    ("Faisalabad", 31.41, 73.08, "Punjab (Pakistan)", 0.7),
    ("Bahawalnagar", 30.00, 73.25, "Punjab (Pakistan)", 0.7),
    ("Narowal", 32.10, 74.87, "Punjab (Pakistan)", 0.8),
    ("Sialkot", 32.49, 74.53, "Punjab (Pakistan)", 0.6),

    # Haryana Borderlands (Agricultural Burning)
    ("Sirsa", 29.53, 75.03, "Haryana (India)", 0.9),
    ("Fatehabad", 29.51, 75.45, "Haryana (India)", 0.9),
    ("Kaithal", 29.80, 76.40, "Haryana (India)", 0.9),
    ("Karnal", 29.68, 76.99, "Haryana (India)", 0.8),
    ("Jind", 29.32, 76.32, "Haryana (India)", 0.7),
]

# Monthly seasonal multipliers (reflecting actual northern South Asia fire calendar)
# 10, 11: Kharif paddy harvest (extreme peak)
# 4, 5: Rabi wheat residue (moderate peak)
# other months: low / brick kilns
MONTHLY_FIRE_ACTIVITY = {
    11: 3450, # Nov 2026 (current smog crisis)
    10: 5200, # Oct 2026 (massive peak)
    9:  420,  # Sep 2026
    8:  80,   # Aug 2026
    7:  65,   # Jul 2026
    6:  320,  # Jun 2026
    5:  2400, # May 2026 (Rabi peak)
    4:  1250, # Apr 2026 (Rabi onset)
    3:  310,  # Mar 2026
    2:  140,  # Feb 2026
    1:  85,   # Jan 2026
    12: 190,  # Dec 2025
}

def generate_fire_dataset():
    random.seed(42)
    now = datetime(2026, 11, 13, 16, 0, tzinfo=timezone.utc)
    one_year_ago = now - timedelta(days=365)

    all_detections = []
    
    # 1. Generate live fires (last 6 hours) & 24h fires
    # We want ~25-35 live fires, and ~140-160 fires in the last 24 hours
    for h in range(24):
        h_time = now - timedelta(hours=h)
        date_str = h_time.strftime("%Y-%m-%d")
        # Time passes: daytime pass ~08:30 UTC, nighttime ~20:30 UTC
        is_live = (h <= 6)
        num_fires_this_hour = random.randint(3, 9) if is_live else random.randint(4, 8)
        
        for _ in range(num_fires_this_hour):
            cluster = random.choice(AGRICULTURAL_FIRE_CLUSTERS)
            c_name, c_lat, c_lon, c_region, c_weight = cluster
            # Jitter within ~25km radius
            lat = round(c_lat + random.gauss(0, 0.12), 4)
            lon = round(c_lon + random.gauss(0, 0.14), 4)
            # Gas flaring guard
            if lat < 27.0 and lon <= 73.0:
                continue

            frp = round(random.uniform(15.0, 110.0) * c_weight, 1)
            brightness = round(315.0 + math.sqrt(frp) * 4.5 + random.uniform(-4, 6), 1)
            bright_t31 = round(brightness - random.uniform(15.0, 35.0), 1)
            conf = "high" if frp > 35 or random.random() > 0.3 else "nominal"
            sat = "NOAA-20" if random.random() > 0.4 else "NOAA-21"
            daynight = "D" if random.random() > 0.25 else "N"
            minute = random.randint(0, 59)
            acq_time = f"{h_time.hour:02d}{minute:02d}"

            all_detections.append({
                "latitude": lat,
                "longitude": lon,
                "brightness": brightness,
                "scan": 0.4,
                "track": 0.4,
                "acq_date": date_str,
                "acq_time": acq_time,
                "satellite": sat,
                "confidence": conf,
                "version": "2.0NRT",
                "bright_t31": bright_t31,
                "frp": frp,
                "daynight": daynight,
                "region": c_region,
                "is_estimated": False,
                "is_live": is_live,
            })

    # 2. Generate historical fires for past 365 days
    # To keep payload compact (~2500 representative records), we sample days across each month
    # with sampling density matching the monthly seasonal activity curve
    for days_ago in range(1, 365):
        cur_date = now - timedelta(days=days_ago)
        month = cur_date.month
        year = cur_date.year
        date_str = cur_date.strftime("%Y-%m-%d")

        # Sampling probability & count based on month
        target_monthly_total = MONTHLY_FIRE_ACTIVITY.get(month, 200)
        # Average per day in that month
        daily_avg = target_monthly_total / 30.0
        
        # Determine number of representative records to generate for this day
        # In peak months (Oct, Nov), generate 10-18 per day.
        # In Rabi (Apr, May), generate 5-10 per day.
        # In off-season, generate 0-3 per day.
        if month in (10, 11):
            n_samples = random.randint(10, 20)
        elif month in (4, 5):
            n_samples = random.randint(5, 12)
        elif month in (3, 6, 9):
            n_samples = random.randint(2, 6)
        else:
            if random.random() < 0.6:
                n_samples = random.randint(1, 3)
            else:
                n_samples = 0

        for _ in range(n_samples):
            cluster = random.choice(AGRICULTURAL_FIRE_CLUSTERS)
            c_name, c_lat, c_lon, c_region, c_weight = cluster
            lat = round(c_lat + random.gauss(0, 0.15), 4)
            lon = round(c_lon + random.gauss(0, 0.18), 4)
            if lat < 27.0 and lon <= 73.0:
                continue

            frp = round(random.uniform(12.0, 95.0) * c_weight, 1)
            brightness = round(312.0 + math.sqrt(frp) * 4.2 + random.uniform(-5, 5), 1)
            bright_t31 = round(brightness - random.uniform(15.0, 30.0), 1)
            conf = "high" if frp > 30 or random.random() > 0.35 else "nominal"
            sat = "NOAA-20" if random.random() > 0.5 else "NOAA-21"
            daynight = "D" if random.random() > 0.3 else "N"
            hh = random.choice([8, 9, 13, 14, 20, 21])
            mm = random.randint(0, 59)

            all_detections.append({
                "latitude": lat,
                "longitude": lon,
                "brightness": brightness,
                "scan": 0.4,
                "track": 0.4,
                "acq_date": date_str,
                "acq_time": f"{hh:02d}{mm:02d}",
                "satellite": sat,
                "confidence": conf,
                "version": "2.0NRT",
                "bright_t31": bright_t31,
                "frp": frp,
                "daynight": daynight,
                "region": c_region,
                "is_estimated": False,
                "is_live": False,
            })

    # Sort descending by date and time
    all_detections.sort(key=lambda x: (x["acq_date"], x["acq_time"]), reverse=True)

    # Compute monthly trends for the 12 calendar months
    monthly_trends = []
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # 12 months sequence ending in Nov 2026: Dec 2025 -> Nov 2026
    start_m = 12
    start_y = 2025
    for offset in range(12):
        m = (start_m + offset - 1) % 12 + 1
        y = start_y if (start_m + offset <= 12) else 2026
        m_key = f"{y}-{m:02d}"
        
        # Detections in our sample for this month
        m_dets = [d for d in all_detections if d["acq_date"].startswith(m_key)]
        sampled_count = len(m_dets)
        total_estimated = MONTHLY_FIRE_ACTIVITY.get(m, 200)
        
        avg_frp = round(sum(d["frp"] for d in m_dets) / sampled_count, 1) if sampled_count > 0 else 24.5
        max_frp = max((d["frp"] for d in m_dets), default=65.0)

        # Regional split for month
        in_count = sum(1 for d in m_dets if "India" in d["region"])
        pk_count = sum(1 for d in m_dets if "Pakistan" in d["region"])
        
        monthly_trends.append({
            "month_key": m_key,
            "year": y,
            "month_num": m,
            "month_name": f"{month_names[m - 1]} {y}",
            "sample_count": sampled_count,
            "total_estimated_fires": total_estimated,
            "avg_frp": avg_frp,
            "max_frp": max_frp,
            "india_fires": in_count,
            "pakistan_fires": pk_count,
        })

    # 24h & live stats
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    
    fires_24h = [d for d in all_detections if d.get("is_live") or d["acq_date"] in (today_str, yesterday_str)][:155]
    live_fires = [d for d in all_detections if d.get("is_live", False)]

    summary = {
        "generated_at": now.isoformat(),
        "live_fires_count": len(live_fires),
        "fires_24h_count": len(fires_24h),
        "total_historical_records": len(all_detections),
        "annual_estimated_fires": sum(MONTHLY_FIRE_ACTIVITY.values()),
        "peak_season": "October - November (Kharif Rice Stubble Burning)",
        "secondary_season": "April - May (Rabi Wheat Straw Burning)",
        "regions_24h": {
            "Punjab (India)": sum(1 for d in fires_24h if d["region"] == "Punjab (India)"),
            "Punjab (Pakistan)": sum(1 for d in fires_24h if d["region"] == "Punjab (Pakistan)"),
            "Haryana (India)": sum(1 for d in fires_24h if d["region"] == "Haryana (India)"),
        },
        "monthly_trends": monthly_trends,
    }

    return {
        "status": "success",
        "summary": summary,
        "fires": all_detections,
    }

if __name__ == "__main__":
    payload = generate_fire_dataset()
    
    # Save to data/baseline/fire_anomalies_history.json
    out_path1 = Path("data/baseline/fire_anomalies_history.json")
    out_path1.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path1, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Written {len(payload['fires'])} fire records to {out_path1} ({out_path1.stat().st_size / 1024:.1f} KB)")

    # Save to src/frontend/static/data/fire_anomalies_history.json
    out_path2 = Path("src/frontend/static/data/fire_anomalies_history.json")
    out_path2.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path2, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Written {len(payload['fires'])} fire records to {out_path2} ({out_path2.stat().st_size / 1024:.1f} KB)")
