#!/usr/bin/env python3
import os
import csv
import math
from collections import defaultdict
from statistics import pstdev
from datetime import datetime

# Try pandas for flexible parsing; fallback to csv if unavailable
USE_PANDAS = False
try:
    import pandas as pd  # type: ignore
    USE_PANDAS = True
except Exception:
    USE_PANDAS = False

WORKDIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(WORKDIR, "temperatures")

OUT_AVG = os.path.join(WORKDIR, "average_temp.txt")
OUT_RANGE = os.path.join(WORKDIR, "largest_temp_range_station.txt")
OUT_STAB = os.path.join(WORKDIR, "temperature_stability_stations.txt")

SEASON_BY_MONTH = {
    12: "Summer", 1: "Summer", 2: "Summer",
    3: "Autumn", 4: "Autumn", 5: "Autumn",
    6: "Winter", 7: "Winter", 8: "Winter",
    9: "Spring", 10: "Spring", 11: "Spring",
}

# Accepted column name variants (lowercased)
STATION_COLS = {"station", "station_id", "station name", "station_name", "id", "site", "site_name", "site id", "siteid"}
TEMP_COLS = {"temperature", "temp", "tmean", "tavg", "air_temperature", "air temp", "air_temp", "value", "mean temperature", "mean temperature (°c)", "mean temp", "temp (c)", "temperature (c)", "t"}
DATE_COLS = {"date", "datetime", "timestamp", "time", "obs_date", "date_time", "dt"}
YEAR_COLS = {"year", "yr"}
MONTH_COLS = {"month", "mon", "mn"}

MONTH_NAME_TO_NUM = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def safe_float(x):
    try:
        v = float(x)
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None

def month_from_any(date_val):
    # Accepts str/datetime/int/month-name
    if date_val is None:
        return None
    if isinstance(date_val, datetime):
        return date_val.month
    if isinstance(date_val, (int, float)):
        m = int(date_val)
        if 1 <= m <= 12:
            return m
        return None
    s = str(date_val).strip()
    if not s:
        return None

    # Try parse int month in string
    if s.isdigit():
        m = int(s)
        return m if 1 <= m <= 12 else None

    # Try month names
    key = s.lower()
    key = key.replace(".", "")
    if key in MONTH_NAME_TO_NUM:
        return MONTH_NAME_TO_NUM[key]

    # Try common date formats
    fmts = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%Y-%m", "%Y/%m", "%m/%Y",
        "%d %b %Y", "%d %B %Y",
        "%b %Y", "%B %Y",
        "%Y%m%d",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.month
        except Exception:
            pass
    # Try ISO
    try:
        dt = datetime.fromisoformat(s)
        return dt.month
    except Exception:
        return None

def normalize_headers(headers):
    return [h.strip().lower() for h in headers]

def pick_col(headers, candidates):
    for h in headers:
        if h in candidates:
            return h
    return None

def guess_temp_col(headers):
    # heuristic: prefer columns containing 'temp' or 'temperature'
    priority = []
    for h in headers:
        hl = h.lower()
        if "temp" in hl or "temperature" in hl:
            priority.append(h)
    if priority:
        return sorted(priority, key=len)[0]
    return None

def read_rows_with_csv(path):
    out = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        sniffer = csv.Sniffer()
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = sniffer.sniff(sample)
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if reader.fieldnames is None:
            return out
        headers = normalize_headers(reader.fieldnames)
        colmap = {orig: norm for orig, norm in zip(reader.fieldnames, headers)}
        station_col = pick_col(headers, STATION_COLS)
        temp_col = pick_col(headers, TEMP_COLS) or guess_temp_col(headers)
        date_col = pick_col(headers, DATE_COLS)
        year_col = pick_col(headers, YEAR_COLS)
        month_col = pick_col(headers, MONTH_COLS)

        for row in reader:
            # Normalize keys
            row = {colmap.get(k, k): v for k, v in row.items()}
            station = row.get(station_col) if station_col else None
            if station is None or str(station).strip() == "":
                station = None
            temp = safe_float(row.get(temp_col)) if temp_col else None
            if temp is None:
                continue  # ignore missing temperature values
            m = None
            if date_col:
                m = month_from_any(row.get(date_col))
            if m is None and (year_col and month_col):
                m = month_from_any(row.get(month_col))
            if m is None and month_col:
                m = month_from_any(row.get(month_col))
            if m is None:
                continue
            out.append((station, m, temp))
    return out

def read_rows_with_pandas(path):
    df = pd.read_csv(path)
    if df.empty:
        return []
    cols = [c.strip().lower() for c in df.columns]
    colmap = {orig: norm for orig, norm in zip(df.columns, cols)}
    station_col = next((c for c in cols if c in STATION_COLS), None)
    temp_col = next((c for c in cols if c in TEMP_COLS), None) or guess_temp_col(cols)
    date_col = next((c for c in cols if c in DATE_COLS), None)
    month_col = next((c for c in cols if c in MONTH_COLS), None)
    year_col = next((c for c in cols if c in YEAR_COLS), None)

    if temp_col is None:
        return []

    # Drop NaN temps
    tseries = pd.to_numeric(df[colmap_inv(colmap, temp_col)], errors="coerce")
    df = df.assign(_temp=tseries).dropna(subset=["_temp"])

    # Month extraction
    m = None
    if date_col:
        dc = colmap_inv(colmap, date_col)
        try:
            dts = pd.to_datetime(df[dc], errors="coerce", dayfirst=True, infer_datetime_format=True)
            m = dts.dt.month
        except Exception:
            m = None
    if m is None and month_col:
        mc = colmap_inv(colmap, month_col)
        m = df[mc].apply(month_from_any)
    if m is None and (year_col and month_col):
        mc = colmap_inv(colmap, month_col)
        m = df[mc].apply(month_from_any)
    if m is None:
        return []

    if station_col:
        sc = colmap_inv(colmap, station_col)
        station_vals = df[sc].astype(str).where(df[sc].notna(), None)
    else:
        station_vals = [None] * len(df)

    out = []
    for station, month, temp in zip(station_vals, m, df["_temp"].astype(float)):
        if month is None or not (1 <= int(month) <= 12):
            continue
        out.append((station, int(month), float(temp)))
    return out

def colmap_inv(colmap, value):
    # find original column for normalized name
    for k, v in colmap.items():
        if v == value:
            return k
    return value

def load_all_records():
    records = []  # list of (station:str|None, month:int, temp:float)
    if not os.path.isdir(TEMP_DIR):
        print(f"Directory not found: {TEMP_DIR}")
        return records
    files = [os.path.join(TEMP_DIR, f) for f in os.listdir(TEMP_DIR) if f.lower().endswith(".csv")]
    files.sort()
    print(f"Found {len(files)} CSV files in {TEMP_DIR}")
    for path in files:
        try:
            if USE_PANDAS:
                rows = read_rows_with_pandas(path)
            else:
                rows = read_rows_with_csv(path)
            print(f"  {os.path.basename(path)}: {len(rows)} records")
            records.extend(rows)
        except Exception as e:
            print(f"  Error reading {os.path.basename(path)}: {e}")
            continue
    return records

def format_celsius(x):
    return f"{x:.1f}°C"

def compute_seasonal_average(records):
    by_season = defaultdict(list)
    for station, month, temp in records:
        season = SEASON_BY_MONTH.get(month)
        if season:
            by_season[season].append(temp)
    result = {}
    for season in ["Summer", "Autumn", "Winter", "Spring"]:
        vals = by_season.get(season, [])
        if vals:
            avg = sum(vals) / len(vals)
            result[season] = avg
    return result

def compute_station_stats(records):
    # Aggregate per station (None → "Unknown")
    temps_by_station = defaultdict(list)
    for station, month, temp in records:
        key = (station.strip() if isinstance(station, str) else station) or "Unknown"
        temps_by_station[key].append(temp)

    # Range
    range_info = {}
    for st, vals in temps_by_station.items():
        if not vals:
            continue
        tmax = max(vals)
        tmin = min(vals)
        rng = tmax - tmin
        range_info[st] = (rng, tmax, tmin)

    # Stability via population std dev (pstdev). If only one value, stddev = 0.0
    std_info = {}
    for st, vals in temps_by_station.items():
        if len(vals) == 0:
            continue
        if len(vals) == 1:
            std = 0.0
        else:
            std = pstdev(vals)
        std_info[st] = std

    return temps_by_station, range_info, std_info

def write_seasonal_average(avg_by_season):
    lines = []
    for season in ["Summer", "Autumn", "Winter", "Spring"]:
        if season in avg_by_season:
            lines.append(f"{season}: {format_celsius(avg_by_season[season])}")
    with open(OUT_AVG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def write_largest_range(range_info):
    if not range_info:
        with open(OUT_RANGE, "w", encoding="utf-8") as f:
            f.write("")
        return
    max_range = max(r for r, _, _ in range_info.values())
    winners = [st for st, (r, _, _) in range_info.items() if abs(r - max_range) < 1e-12]
    winners.sort()
    lines = []
    for st in winners:
        r, tmax, tmin = range_info[st]
        lines.append(f"{st}: Range {format_celsius(r)} (Max: {format_celsius(tmax)}, Min: {format_celsius(tmin)})")
    with open(OUT_RANGE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def write_stability(std_info):
    if not std_info:
        with open(OUT_STAB, "w", encoding="utf-8") as f:
            f.write("")
        return
    min_std = min(std_info.values())
    max_std = max(std_info.values())

    most_stable = sorted([st for st, s in std_info.items() if abs(s - min_std) < 1e-12])
    most_variable = sorted([st for st, s in std_info.items() if abs(s - max_std) < 1e-12])

    stable_names = ", ".join(most_stable)
    variable_names = ", ".join(most_variable)

    lines = [
        f"Most Stable: {stable_names}: StdDev {format_celsius(min_std)}",
        f"Most Variable: {variable_names}: StdDev {format_celsius(max_std)}",
    ]
    with open(OUT_STAB, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    records = load_all_records()
    if not records:
        # Ensure outputs exist, even if empty
        open(OUT_AVG, "w", encoding="utf-8").close()
        open(OUT_RANGE, "w", encoding="utf-8").close()
        open(OUT_STAB, "w", encoding="utf-8").close()
        print("No records loaded. Check 'temperatures' folder and CSV headers (temp/date or month).")
        return

    print(f"Total records loaded: {len(records)}")
    avg_by_season = compute_seasonal_average(records)
    _, range_info, std_info = compute_station_stats(records)

    write_seasonal_average(avg_by_season)
    write_largest_range(range_info)
    write_stability(std_info)
    print("Analysis complete. Check output files.")

if __name__ == "__main__":
    main()
