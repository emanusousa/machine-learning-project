import io
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()

AWS_BUCKET = os.getenv("AWS_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

THINGSBOARD_URL = os.getenv("THINGSBOARD_URL")
THINGSBOARD_DEVICE_ID = os.getenv("THINGSBOARD_DEVICE_ID")
THINGSBOARD_TENANT_USER = os.getenv("THINGSBOARD_TENANT_USER")
THINGSBOARD_TENANT_PASSWORD = os.getenv("THINGSBOARD_TENANT_PASSWORD")

if not all(
    [
        AWS_BUCKET,
        AWS_REGION,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        THINGSBOARD_URL,
        THINGSBOARD_DEVICE_ID,
        THINGSBOARD_TENANT_USER,
        THINGSBOARD_TENANT_PASSWORD,
    ]
):
    raise RuntimeError(
        "Some required environment variables are missing in fastapi/.env"
    )

# -------------------------------------------------------------------
# AWS S3 client
# -------------------------------------------------------------------
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="ThingsBoard → S3 Ingestion Service")


# -------------------------------------------------------------------
# ThingsBoard helpers
# -------------------------------------------------------------------
def get_thingsboard_token() -> str:
    """
    Authenticate as tenant user and return JWT token.
    """
    url = f"{THINGSBOARD_URL}/api/auth/login"
    payload = {
        "username": THINGSBOARD_TENANT_USER,
        "password": THINGSBOARD_TENANT_PASSWORD,
    }

    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        logger.error(f"Failed to login to ThingsBoard: {resp.status_code} {resp.text}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authenticate with ThingsBoard.",
        )

    data = resp.json()
    token = data.get("token")
    if not token:
        logger.error("ThingsBoard login response has no 'token' field.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ThingsBoard login did not return a token.",
        )

    return token


def fetch_thingsboard_telemetry(token: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch full timeseries data for the heart dataset from ThingsBoard.

    We request the time window from 0 to 'now', with a large limit,
    and no aggregation (agg=NONE).
    """
    url = f"{THINGSBOARD_URL}/api/plugins/telemetry/DEVICE/{THINGSBOARD_DEVICE_ID}/values/timeseries"

    END_TS = 2_000_000_000_000

    params = {
        "keys": "age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca,thal,target",
        "startTs": 0,
        "endTs": END_TS,
        "limit": 5000,
        "agg": "NONE",
        "interval": 0,
    }

    headers = {"X-Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers, params=params, timeout=20)
    if resp.status_code != 200:
        logger.error(
            f"Failed to fetch telemetry from ThingsBoard: {resp.status_code} {resp.text}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch telemetry from ThingsBoard (status={resp.status_code}).",
        )

    data = resp.json()
    if not isinstance(data, dict) or not data:
        logger.error(f"Empty or invalid telemetry response from ThingsBoard: {data}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ThingsBoard telemetry response is empty or invalid.",
        )

    return data


def telemetry_to_dataframe(data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Convert ThingsBoard timeseries JSON into a pandas DataFrame.

    The input format is something like:
    {
      "age":   [ {"ts": 123, "value": "63"}, {"ts": 124, "value": "37"}, ... ],
      "chol":  [ {"ts": 123, "value": "233"}, {"ts": 124, "value": "250"}, ... ],
      ...
    }

    We merge all series on 'ts' so each row corresponds to one timestamp.
    """
    df: pd.DataFrame | None = None

    for key, series in data.items():
        if not series:
            # no data for this key
            logger.warning(f"No data for key '{key}' in ThingsBoard response.")
            continue

        key_df = pd.DataFrame(series)[["ts", "value"]]
        # convert numeric fields
        key_df["value"] = pd.to_numeric(key_df["value"], errors="coerce")
        key_df = key_df.rename(columns={"value": key})

        if df is None:
            df = key_df
        else:
            df = df.merge(key_df, on="ts", how="outer")

    if df is None or df.empty:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No telemetry data could be converted to DataFrame.",
        )

    # Sort by timestamp and reset index
    df = df.sort_values("ts").reset_index(drop=True)

    return df


def upload_dataframe_to_s3(df: pd.DataFrame) -> str:
    """
    Serialize DataFrame to CSV in memory and upload to S3.
    Returns the S3 key used.
    """
    # Generate key
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"heart/raw/heart_telemetry_{now_utc}.csv"

    # Serialize to CSV (in memory)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    body = buffer.getvalue().encode("utf-8")

    logger.info(f"Uploading telemetry CSV to s3://{AWS_BUCKET}/{key} (rows={len(df)})")
    s3_client.put_object(Bucket=AWS_BUCKET, Key=key, Body=body)
    logger.info("Upload completed.")

    return key


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "ThingsBoard ingestion service is running.",
        "endpoints": ["/ingest/heart"],
    }


@app.post("/ingest/heart")
async def ingest_heart():
    """
    Fetch full heart telemetry from ThingsBoard and store it as CSV in S3.
    """
    try:
        token = get_thingsboard_token()
        tb_data = fetch_thingsboard_telemetry(token)
        df = telemetry_to_dataframe(tb_data)
        s3_key = upload_dataframe_to_s3(df)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Telemetry ingested and stored in S3 successfully.",
                "s3_key": s3_key,
                "rows": int(len(df)),
            },
        )
    except HTTPException:
        # re-raise FastAPI HTTP errors
        raise
    except Exception as exc:
        logger.exception("Unexpected error while ingesting telemetry.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while ingesting telemetry: {exc}",
        )
