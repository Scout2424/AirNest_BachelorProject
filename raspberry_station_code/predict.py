#!/usr/bin/env python3
"""
predict.py — Air Quality 7-Day Predictor
Raspberry Pi deployment script.

Location: /home/guestguy216/Desktop/sensor_station2026/predict.py

Run daily via cron:
    0 7 * * * /usr/bin/python3 /home/guestguy216/Desktop/sensor_station2026/predict.py

Install dependencies once:
    pip install prophet scikit-learn pandas numpy requests joblib --break-system-packages
"""

import os
import json
import logging
import requests
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_DIR   = Path("/home/guestguy216/Desktop/sensor_station2026")
MODELS_DIR = BASE_DIR / "models"
DATA_DIR   = BASE_DIR / "data"
OUTPUT_CSV = DATA_DIR / "predictions.csv"
SENSOR_CSV = BASE_DIR / "sensor_data_log.csv"   # written by your air station script

FLASK_URL    = "http://13.61.152.65:8080/api/predictions"
FLASK_SECRET = "airquality2026"                  # must match PREDICTION_SECRET in app.py

LAT, LON = 45.7489, 21.2087                     # Timișoara
LOG_FILE = BASE_DIR / "predict.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

def fetch_weather_forecast():
    """Fetch 7-day forecast from Open-Meteo (free, no API key needed)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        f"relative_humidity_2m_mean,weathercode"
        f"&timezone=Europe%2FBucharest"
        f"&forecast_days=7"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    d = resp.json()["daily"]
    df = pd.DataFrame({
        "date":          pd.to_datetime(d["time"]),
        "temp_c_max":    d["temperature_2m_max"],
        "temp_c_min":    d["temperature_2m_min"],
        "temp_c_mean":   d["temperature_2m_mean"],
        "humidity_mean": d["relative_humidity_2m_mean"],
        "weathercode":   d["weathercode"],
    })
    df["is_rainy"] = df["weathercode"].apply(lambda c: 1 if c >= 51 else 0)
    return df


def load_recent_sensor(n_days=30):
    """
    Load the last n_days from sensor_data_log.csv (written by your air station script).
    Returns a daily-aggregated DataFrame with mean PPM and temp/humidity values.
    """
    if not SENSOR_CSV.exists():
        log.warning("Sensor CSV not found at: %s", SENSOR_CSV)
        return pd.DataFrame()

    df = pd.read_csv(SENSOR_CSV)

    # Parse the date from your CSV format: Year=2026, Month=May, Day="Sunday 24"
    def parse_date(row):
        try:
            day_num = str(row["Day"]).split()[-1]   # "Sunday 24" → "24"
            return pd.to_datetime(
                f"{row['Year']} {row['Month']} {day_num}", format="%Y %B %d"
            )
        except Exception:
            return pd.NaT

    df["date"] = df.apply(parse_date, axis=1)

    # Drop rows with bad temperature (0.0°C = DHT11 failure) and missing dates
    df = df[df["Temperature_C"] > 1.0].dropna(subset=["date"])

    # Replace "N/A" strings (from your Pi script) with actual NaN
    ppm_cols = ["MQ135_ppm", "MQ3_ppm", "MQ6_ppm", "MQ7_ppm", "MQ8_ppm"]
    for col in ppm_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep only last n_days
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=n_days)
    df = df[df["date"] >= cutoff]

    if df.empty:
        log.warning("No sensor rows in the last %d days", n_days)
        return pd.DataFrame()

    # Aggregate to daily means
    daily = df.groupby("date").agg(
        **{col + "_mean": (col, "mean") for col in ppm_cols},
        temp_sensor_mean = ("Temperature_C", "mean"),
        humidity_sensor  = ("Humidity",       "mean"),
        n_readings       = ("MQ135_ppm",      "count"),
    ).reset_index()

    log.info("Sensor data loaded: %d days (%d total readings)", len(daily), df.shape[0])
    return daily.sort_values("date").reset_index(drop=True)


def build_feature_row(future_date, weather_row, sensor_recent, meta):
    """Build one feature vector for a single future date."""
    feature_cols = meta["feature_cols"]
    season_map   = {12:0, 1:0, 2:0, 3:1, 4:1, 5:1,
                     6:2, 7:2, 8:2, 9:3, 10:3, 11:3}

    row = {
        "date":          future_date,
        "temp_c_mean":   weather_row.get("temp_c_mean",   20.0),
        "temp_c_max":    weather_row.get("temp_c_max",    25.0),
        "temp_c_min":    weather_row.get("temp_c_min",    15.0),
        "humidity_mean": weather_row.get("humidity_mean", 50.0),
        "is_rainy":      int(weather_row.get("is_rainy",   0)),
        "dayofyear":     future_date.dayofyear,
        "month":         future_date.month,
        "weekofyear":    future_date.isocalendar()[1],
        "season":        season_map[future_date.month],
    }

    # Lag / roll features from recent sensor history
    if len(sensor_recent) >= 1:
        last = sensor_recent.iloc[-1]
        row["temp_lag1"]     = last.get("temp_sensor_mean", row["temp_c_mean"])
        row["humidity_lag1"] = last.get("humidity_sensor",  row["humidity_mean"])
        for col in ["MQ135_ppm_mean", "MQ3_ppm_mean", "MQ6_ppm_mean",
                    "MQ7_ppm_mean",   "MQ8_ppm_mean"]:
            row[col] = last.get(col, np.nan)
    else:
        row["temp_lag1"]     = row["temp_c_mean"]
        row["humidity_lag1"] = row["humidity_mean"]

    if len(sensor_recent) >= 7:
        tail7 = sensor_recent.tail(7)
        row["temp_lag7"]      = tail7.iloc[0].get("temp_sensor_mean", row["temp_c_mean"])
        row["temp_roll7"]     = tail7["temp_sensor_mean"].mean()
        row["humidity_roll7"] = tail7["humidity_sensor"].mean()
    else:
        row["temp_lag7"]      = row["temp_c_mean"]
        row["temp_roll7"]     = row["temp_c_mean"]
        row["humidity_roll7"] = row["humidity_mean"]

    # Fill any feature the model expects but we don't have a value for
    for col in feature_cols:
        if col not in row:
            row[col] = 0.0

    return row


def run_prophet_forecast(model_path, periods=8):
    """Load a saved Prophet model and return a forecast DataFrame."""
    try:
        model  = joblib.load(model_path)
        future = model.make_future_dataframe(periods=periods)
        fc     = model.predict(future).tail(periods)
        return fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].reset_index(drop=True)
    except Exception as e:
        log.error("Prophet load/predict failed (%s): %s", model_path, e)
        return None


def post_to_flask(predictions_df):
    """POST the 7-day predictions as JSON to the Flask server on AWS."""
    try:
        payload = predictions_df.to_dict(orient="records")
        for row in payload:
            row["date"] = str(row["date"])[:10]   # ensure plain string "YYYY-MM-DD"

        resp = requests.post(
            FLASK_URL,
            json={"predictions": payload},
            headers={"X-Secret": FLASK_SECRET},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Predictions POSTed to Flask — HTTP %s", resp.status_code)
        return True
    except Exception as e:
        log.error("Failed to POST predictions to Flask: %s", e)
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    log.info("=== predict.py started ===")

    # Make sure data/ folder exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load model metadata ────────────────────────────────────────────────────
    meta_path = MODELS_DIR / "model_meta.json"
    if not meta_path.exists():
        log.error("model_meta.json not found in %s — aborting", MODELS_DIR)
        print(f"❌  model_meta.json not found in {MODELS_DIR}")
        print("    Copy the 4 model files from Colab into the models/ folder first.")
        return

    with open(meta_path) as f:
        meta = json.load(f)
    log.info("Model meta loaded (trained %s, %d features)",
             meta["trained_on"], len(meta["feature_cols"]))
    print(f"✅  Model meta loaded  (trained {meta['trained_on']},"
          f" {len(meta['feature_cols'])} features)")

    # ── Load Random Forest ─────────────────────────────────────────────────────
    rf_path = MODELS_DIR / "rf_danger_classifier.pkl"
    if not rf_path.exists():
        log.error("rf_danger_classifier.pkl not found — aborting")
        print(f"❌  rf_danger_classifier.pkl not found in {MODELS_DIR}")
        return

    rf = joblib.load(rf_path)
    log.info("Random Forest classifier loaded")
    print("✅  Random Forest classifier loaded")

    # ── Fetch 7-day weather forecast ───────────────────────────────────────────
    print("🌤  Fetching 7-day weather forecast from Open-Meteo...")
    try:
        weather_fc = fetch_weather_forecast()
        log.info("Weather forecast fetched: %d days", len(weather_fc))
        print(f"✅  Weather forecast: {len(weather_fc)} days")
    except Exception as e:
        log.error("Weather fetch failed: %s — will use fallback values", e)
        print(f"⚠️   Weather fetch failed ({e}) — using fallback values")
        weather_fc = pd.DataFrame()

    # ── Load recent sensor readings ────────────────────────────────────────────
    print("📂  Loading recent sensor data...")
    sensor_recent = load_recent_sensor(n_days=30)
    if sensor_recent.empty:
        print("⚠️   No recent sensor data found — lag features will use weather defaults")
    else:
        print(f"✅  Sensor data: {len(sensor_recent)} days of readings")

    # ── Run Prophet forecasts ──────────────────────────────────────────────────
    print("🔮  Running Prophet forecasts...")
    fc_temp = run_prophet_forecast(MODELS_DIR / "prophet_temperature.pkl")
    fc_hum  = run_prophet_forecast(MODELS_DIR / "prophet_humidity.pkl")

    if fc_temp is not None:
        print("✅  Prophet temperature forecast ready")
    else:
        print("⚠️   Prophet temperature model missing — using Open-Meteo values instead")

    if fc_hum is not None:
        print("✅  Prophet humidity forecast ready")
    else:
        print("⚠️   Prophet humidity model missing — using Open-Meteo values instead")

    # ── Build feature rows for the next 7 days ─────────────────────────────────
    records = []
    today   = pd.Timestamp.today().normalize()

    for i in range(7):
        future_date = today + pd.Timedelta(days=i + 1)
        w_row       = weather_fc.iloc[i].to_dict() if len(weather_fc) > i else {}
        feat        = build_feature_row(future_date, w_row, sensor_recent, meta)
        records.append(feat)

    feature_cols = meta["feature_cols"]
    X_future     = pd.DataFrame(records)[feature_cols].fillna(0)

    # ── Predict danger ─────────────────────────────────────────────────────────
    danger_pred  = rf.predict(X_future)
    danger_proba = rf.predict_proba(X_future)[:, 1]

    # ── Assemble output rows ───────────────────────────────────────────────────
    out_rows = []
    for i, rec in enumerate(records):
        date = rec["date"]

        # Temperature: prefer Prophet, fall back to Open-Meteo
        if fc_temp is not None:
            fc_t          = fc_temp[fc_temp["ds"] == date]
            temp_forecast = round(fc_t["yhat"].values[0],       1) if len(fc_t) else rec["temp_c_mean"]
            temp_low      = round(fc_t["yhat_lower"].values[0], 1) if len(fc_t) else rec["temp_c_min"]
            temp_high     = round(fc_t["yhat_upper"].values[0], 1) if len(fc_t) else rec["temp_c_max"]
        else:
            temp_forecast = round(rec.get("temp_c_mean", 20.0), 1)
            temp_low      = round(rec.get("temp_c_min",  15.0), 1)
            temp_high     = round(rec.get("temp_c_max",  25.0), 1)

        # Humidity: prefer Prophet, fall back to Open-Meteo
        if fc_hum is not None:
            fc_h         = fc_hum[fc_hum["ds"] == date]
            hum_forecast = round(fc_h["yhat"].values[0], 1) if len(fc_h) else rec["humidity_mean"]
        else:
            hum_forecast = round(rec.get("humidity_mean", 50.0), 1)

        out_rows.append({
            "date":               str(date)[:10],
            "temp_forecast_c":    temp_forecast,
            "temp_low_c":         temp_low,
            "temp_high_c":        temp_high,
            "humidity_forecast":  hum_forecast,
            "danger_predicted":   int(danger_pred[i]),
            "danger_label":       "DANGER" if danger_pred[i] == 1 else "SAFE",
            "danger_probability": round(float(danger_proba[i]), 3),
            "is_rainy_forecast":  int(rec.get("is_rainy", 0)),
            "generated_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    out_df = pd.DataFrame(out_rows)

    # ── Save to local CSV ──────────────────────────────────────────────────────
    write_header = not OUTPUT_CSV.exists()
    out_df.to_csv(OUTPUT_CSV, mode="a", header=write_header, index=False)
    log.info("Predictions saved to %s", OUTPUT_CSV)

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n📅  7-Day Air Quality Prediction")
    print("=" * 68)
    for _, row in out_df.iterrows():
        rain   = "🌧 " if row["is_rainy_forecast"] else "☀️ "
        danger = "⚠️  DANGER" if row["danger_predicted"] else "✅ SAFE  "
        print(
            f"  {row['date']}  {rain}  "
            f"Temp: {row['temp_low_c']:.0f}–{row['temp_high_c']:.0f}°C  "
            f"Hum: {row['humidity_forecast']:.0f}%  "
            f"{danger}  (p={row['danger_probability']:.2f})"
        )
    print("=" * 68)
    print(f"\n💾  Saved to: {OUTPUT_CSV}")

    # ── POST to Flask ──────────────────────────────────────────────────────────
    print("\n📡  Sending predictions to Flask server...")
    posted = post_to_flask(out_df)
    if posted:
        print("✅  Predictions sent to server successfully")
    else:
        print("⚠️   Could not reach Flask server — predictions saved locally only")
        print("     Check predict.log for details")

    log.info("=== predict.py finished ===")


if __name__ == "__main__":
    main()