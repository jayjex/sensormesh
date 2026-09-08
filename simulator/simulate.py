#!/usr/bin/env python3
"""
sensormesh device simulator: synthetic IoT sensor readings with realistic 24h curves.

Three sensor types per mesh, modeled on street-level hardware:
  air_quality : PM2.5 (ug/m3)  -- rush-hour bumps, rain flushing, dust spikes
  temperature : degrees C      -- diurnal curve, coldest ~05:00, hottest ~15:00
  noise       : dB(A)          -- commute rush, daytime activity, night lull

Realism baked in:
  - 24h diurnal envelope per sensor type (site-dependent baselines)
  - Gaussian jitter + slow random-walk drift, so curves wander like real hardware
  - occasional vehicle-passby spikes on noise
  - anomaly injection: spike, stuck value, flatline sensor fault
  - deterministic with --seed, so sample outputs are reproducible

Output: CSV and/or JSONL, one row per reading. Columns:
  timestamp, device_id, site, sensor_type, value, unit, anomaly

Stdlib only.

Examples:
  python3 simulate.py                          # default: 1 day, seed 42, both formats, 1000+ rows
  python3 simulate.py --days 7 --interval 30   # a week at 30-minute cadence
  python3 simulate.py --format csv --out out.csv
"""
import argparse
import csv
import json
import math
import random
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc

# (sensor_type, unit) and per-site baseline + amplitude for the 24h curve.
# sites: metro-core (downtown street), riverside-park (green zone),
# north-industrial (industrial edge). Values are plausible, not lab-grade:
# PM2.5 annual means ~7-30 ug/m3 in most cities, noise 40-75 dB(A) street level.
SENSORS = {
    "air_quality": {"unit": "ug/m3"},
    "temperature": {"unit": "C"},
    "noise": {"unit": "dB"},
}

SITES = {
    "metro-core": {
        "air_quality": {"base": 16.0, "rush_amp": 14.0, "mid_amp": 4.0},
        "temperature": {"base": 22.0, "amp": 5.5},   # urban heat island keeps nights warm
        "noise": {"night": 44.0, "day_peak": 68.0},
    },
    "riverside-park": {
        "air_quality": {"base": 8.0, "rush_amp": 4.0, "mid_amp": 2.0},
        "temperature": {"base": 20.5, "amp": 6.5},
        "noise": {"night": 36.0, "day_peak": 55.0},
    },
    "north-industrial": {
        "air_quality": {"base": 27.0, "rush_amp": 12.0, "mid_amp": 8.0},
        "temperature": {"base": 22.5, "amp": 5.0},
        "noise": {"night": 41.0, "day_peak": 64.0},
    },
}

# 3 sensor types x 3 sites = 9 devices, ids like sm-001..sm-009
DEVICE_ORDER = [
    ("metro-core", "air_quality"), ("metro-core", "temperature"), ("metro-core", "noise"),
    ("riverside-park", "air_quality"), ("riverside-park", "temperature"), ("riverside-park", "noise"),
    ("north-industrial", "air_quality"), ("north-industrial", "temperature"), ("north-industrial", "noise"),
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def gauss_hour(h, center, width):
    """Unnormalized gaussian bump over the hour of day."""
    d = min(abs(h - center), 24 - abs(h - center))  # wrap midnight
    return math.exp(-(d * d) / (2 * width * width))


class Drift:
    """Slow random walk shared by all readings of one device. Real sensors
    wander; pure white noise looks fake."""

    def __init__(self, rng, scale):
        self.rng = rng
        self.scale = scale
        self.w = 0.0

    def step(self):
        self.w += self.rng.gauss(0, self.scale)
        self.w *= 0.995  # mean-revert so a week of drift stays sane
        return self.w


class DeviceSim:
    def __init__(self, num, site, sensor, rng):
        self.device_id = f"sm-{num:03d}"
        self.site = site
        self.sensor = sensor
        self.cfg = SITES[site][sensor]
        self.rng = rng
        self.drift = Drift(rng, {"air_quality": 0.15, "temperature": 0.05, "noise": 0.2}[sensor])
        self.stuck_left = 0       # rows remaining in a stuck-value anomaly
        self.stuck_value = None

    def base_curve(self, hour):
        """Typical value for this hour of day, before noise."""
        c, s = self.cfg, self.sensor
        if s == "temperature":
            # sinusoid peaking 15:00, trough 03:00
            return c["base"] + c["amp"] * math.sin(2 * math.pi * (hour - 9) / 24)
        if s == "air_quality":
            morning = gauss_hour(hour, 8.0, 1.4)
            evening = gauss_hour(hour, 18.0, 1.6)
            midday = gauss_hour(hour, 13.0, 3.5)
            return c["base"] + c["rush_amp"] * (morning + evening) + c["mid_amp"] * midday
        if s == "noise":
            # logistic sunrise ramp, lull after 23:00
            day = 1 / (1 + math.exp(-(hour - 6.5) * 1.2))
            night = 1 / (1 + math.exp(-(hour - 23.5) * 1.5))
            return c["night"] + (c["day_peak"] - c["night"]) * day * (1 - night)
        raise ValueError(s)

    def read(self, ts):
        """One reading at datetime ts. Returns (value, anomaly_flag)."""
        hour = ts.hour + ts.minute / 60.0
        rng = self.rng
        flag = ""
        if self.stuck_left > 0:
            self.stuck_left -= 1
            return self.stuck_value, "stuck"

        v = self.base_curve(hour) + self.drift.step()

        if self.sensor == "temperature":
            v += rng.gauss(0, 0.4)
            v = clamp(v, -10, 45)
        elif self.sensor == "air_quality":
            v *= math.exp(rng.gauss(0, 0.10))  # multiplicative: PM spikes skew high
            v = clamp(v, 1.0, 350.0)
        elif self.sensor == "noise":
            v += rng.gauss(0, 1.1)
            if rng.random() < 0.05:            # vehicle passby
                v += rng.uniform(7, 16)
                flag = "passby"
            v = clamp(v, 30, 110)

        # anomaly injection (independent small probabilities)
        roll = rng.random()
        if roll < 0.010 and flag == "":
            if self.sensor == "noise":
                v += rng.uniform(18, 30)
            elif self.sensor == "temperature":
                v += rng.uniform(8, 15)
            else:
                v *= rng.uniform(2.5, 4.5)
            flag = "spike"
        elif roll < 0.014:
            self.stuck_left = rng.randint(2, 5)
            self.stuck_value = round(v, 1)
            return self.stuck_value, "stuck"
        elif roll < 0.017 and self.sensor == "air_quality":
            v = 0.0                             # sensor fault reads zero
            flag = "flatline"

        return v, flag


def generate(days, interval_min, seed, anomaly=True):
    rng = random.Random(seed)
    devices = [DeviceSim(i + 1, site, sensor, rng)
               for i, (site, sensor) in enumerate(DEVICE_ORDER)]
    start = datetime(2026, 9, 8, 0, 0, tzinfo=UTC)  # fixed window keeps samples reproducible
    steps = int(days * 24 * 60 / interval_min)
    rows = []
    for step in range(steps):
        ts = start + timedelta(minutes=step * interval_min)
        for d in devices:
            v, flag = d.read(ts)
            if not anomaly:
                flag = ""
            rows.append({
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "device_id": d.device_id,
                "site": d.site,
                "sensor_type": d.sensor,
                "value": round(v, 1),
                "unit": SENSORS[d.sensor]["unit"],
                "anomaly": flag,
            })
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_jsonl(rows, path):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def summarize(rows):
    by_type = {}
    for r in rows:
        by_type.setdefault(r["sensor_type"], []).append(r["value"])
    lines = []
    for t, vals in sorted(by_type.items()):
        anom = sum(1 for r in rows if r["sensor_type"] == t and r["anomaly"] in ("spike", "stuck", "flatline"))
        lines.append(f"  {t:12s} n={len(vals):5d}  min={min(vals):7.1f}  mean={statistics.fmean(vals):7.1f}  "
                     f"max={max(vals):7.1f}  anomalies={anom}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="sensormesh device simulator")
    ap.add_argument("--days", type=float, default=1.0)
    ap.add_argument("--interval", type=int, default=10, help="minutes between readings (default 10)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--format", choices=["csv", "jsonl", "both"], default="both")
    ap.add_argument("--out", default=None, help="output path (default data/sensormesh-sample.<ext>)")
    ap.add_argument("--no-anomalies", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="skip the summary print")
    a = ap.parse_args()

    rows = generate(a.days, a.interval, a.seed, anomaly=not a.no_anomalies)
    stem = a.out or f"data/sensormesh-{a.days:g}d-seed{a.seed}"
    exts = {"csv": [".csv"], "jsonl": [".jsonl"], "both": [".csv", ".jsonl"]}[
        a.format] if a.out else [".csv", ".jsonl"]
    base = Path(stem)
    for ext in exts:
        out = base.with_suffix(ext)
        if ext == ".csv":
            write_csv(rows, out)
        else:
            write_jsonl(rows, out)
        if not a.quiet:
            print(f"wrote {out} ({len(rows)} rows)")
    if not a.quiet:
        print(f"devices={len(DEVICE_ORDER)} sites={len(SITES)} span={a.days}d interval={a.interval}min seed={a.seed}")
        print(summarize(rows))


if __name__ == "__main__":
    main()
