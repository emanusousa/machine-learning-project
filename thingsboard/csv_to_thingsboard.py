import os
import time
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

THINGSBOARD_URL = os.getenv("THINGSBOARD_URL")
ACCESS_TOKEN = os.getenv("THINGSBOARD_DEVICE_ACCESS_TOKEN")
CSV_PATH = os.getenv("CSV_PATH")
MLFLOW_URL = os.getenv("MLFLOW_URL")

if not THINGSBOARD_URL or not ACCESS_TOKEN or not CSV_PATH:
    raise RuntimeError("Missing .env variables")


# ---------------------------------------------------------
# Chamada ao MLflow — agora usando nomes UPPERCASE
# ---------------------------------------------------------
def call_mlflow_model(row: pd.Series) -> float:
    features = {
        "AGE": int(row["age"]),
        "SEX": int(row["sex"]),
        "CP": int(row["cp"]),
        "TRESTBPS": int(row["trestbps"]),
        "CHOL": int(row["chol"]),
        "FBS": int(row["fbs"]),
        "RESTECG": int(row["restecg"]),
        "THALACH": int(row["thalach"]),
        "EXANG": int(row["exang"]),
        "OLDPEAK": float(row["oldpeak"]),
        "SLOPE": int(row["slope"]),
        "CA": int(row["ca"]),
        "THAL": int(row["thal"]),
    }

    payload = {
        "dataframe_split": {
            "columns": list(features.keys()),
            "data": [list(features.values())]
        }
    }

    resp = requests.post(MLFLOW_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()

    # mlflow sklearn normalmente retorna {"predictions": [...]}
    if isinstance(data, dict) and "predictions" in data:
        return float(data["predictions"][0])

    raise RuntimeError(f"Unexpected MLflow response: {data}")


# ---------------------------------------------------------
# Envio ao ThingsBoard
# ---------------------------------------------------------
def send_row(row: pd.Series, ts: int, index: int):
    url = f"{THINGSBOARD_URL}/api/v1/{ACCESS_TOKEN}/telemetry"

    try:
        risk = call_mlflow_model(row)
    except Exception as e:
        print(f"[MLFLOW ERROR] row={index}: {e}")
        return

    tb_payload = {
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
            "risk_score": risk,
        }
    }

    r = requests.post(url, json=tb_payload)

    if r.status_code == 200:
        print(f"[OK] {index} | risk={risk:.4f}")
    else:
        print(f"[TB ERROR] row={index}: {r.status_code} - {r.text}")


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Sending {len(df)} rows...")

    base_ts = int(time.time() * 1000)

    for i, (_, row) in enumerate(df.iterrows(), 1):
        ts = base_ts + i * 1000
        send_row(row, ts, i)

    print("FINISHED.")


if __name__ == "__main__":
    main()
