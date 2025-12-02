import os
import time
import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------
load_dotenv()

THINGSBOARD_URL = os.getenv("THINGSBOARD_URL")
ACCESS_TOKEN = os.getenv("THINGSBOARD_DEVICE_ACCESS_TOKEN")
CSV_PATH = os.getenv("CSV_PATH")

if not THINGSBOARD_URL or not ACCESS_TOKEN or not CSV_PATH:
    raise RuntimeError("Missing .env variables")


# ---------------------------------------------------------
# Telemetry sender
# ---------------------------------------------------------
def send_row_as_telemetry(row: pd.Series, ts: int, index: int) -> None:
    url = f"{THINGSBOARD_URL}/api/v1/{ACCESS_TOKEN}/telemetry"

    payload = {
        "ts": ts,
        "values": {
            "age": int(row["age"]),
            "sex": int(row["sex"]),
            "cp": int(row["cp"]),
            "trestbps": int(row["trestbps"]),
            "chol": int(row["chol"]),
            "fbs": int(row["fbs"]),
            "restecg": int(row["restecg"]),
            "thalach": int(row["thalach"]),
            "exang": int(row["exang"]),
            "oldpeak": float(row["oldpeak"]),
            "slope": int(row["slope"]),
            "ca": int(row["ca"]),
            "thal": int(row["thal"]),
            "target": int(row["target"]),
        },
    }

    resp = requests.post(url, json=payload)

    if resp.status_code != 200:
        print("ERROR:", resp.status_code, resp.text)
    else:
        print(f"[OK] row={index} ts={ts}")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    df = pd.read_csv(CSV_PATH)

    print(f"Sending {len(df)} rows...")

    base_ts = int(time.time() * 1000)

    for i, row in enumerate(df.iterrows(), start=1):
        ts = base_ts + i * 1000
        send_row_as_telemetry(row[1], ts, i)

    print("FINISHED.")


if __name__ == "__main__":
    main()
