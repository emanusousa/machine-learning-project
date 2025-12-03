import os
import time
import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------
# Carregar variáveis do .env
# ---------------------------------------------------------
load_dotenv()

THINGSBOARD_URL = os.getenv("THINGSBOARD_URL")
ACCESS_TOKEN = os.getenv("THINGSBOARD_DEVICE_ACCESS_TOKEN")
CSV_PATH = os.getenv("CSV_PATH")
MLFLOW_URL = os.getenv("MLFLOW_URL", "")  # opcional

if not THINGSBOARD_URL or not ACCESS_TOKEN or not CSV_PATH:
    raise RuntimeError("Missing required environment variables (.env)")


# ---------------------------------------------------------
# Fallback de risco (sem MLflow)
# ---------------------------------------------------------
def call_mlflow_model(row: pd.Series) -> float:
    """
    Tenta chamar MLflow. Se não houver MLFLOW_URL configurado
    ou ocorrer erro, retorna risco default = 0.5
    """
    if not MLFLOW_URL:
        return 0.5

    payload = {
        "dataframe_records": [
            {
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
        ]
    }

    try:
        resp = requests.post(MLFLOW_URL, json=payload, timeout=5)
        resp.raise_for_status()
        preds = resp.json().get("predictions")
        return float(preds[0]) if preds else 0.5
    except Exception as e:
        print(f"[MLFLOW ERROR] {e} -> usando risco=0.5")
        return 0.5


# ---------------------------------------------------------
# Enviar linha ao ThingsBoard
# ---------------------------------------------------------
def send_row(row: pd.Series, ts: int, index: int):
    url = f"{THINGSBOARD_URL}/api/v1/{ACCESS_TOKEN}/telemetry"

    risk = call_mlflow_model(row)

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
            "risk_score": float(risk),
        },
    }

    resp = requests.post(url, json=payload)

    if resp.status_code == 200:
        print(f"[OK] row={index}  risk={risk:.3f}")
    else:
        print(f"[TB ERROR] row={index}: {resp.status_code} - {resp.text}")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    print(f"Lendo CSV de: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"Enviando {len(df)} linhas...")

    base_ts = int(time.time() * 1000)

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        ts = base_ts + i * 1000
        send_row(row, ts, i)

    print("FINISHED CSV LOAD.")


if __name__ == "__main__":
    main()
