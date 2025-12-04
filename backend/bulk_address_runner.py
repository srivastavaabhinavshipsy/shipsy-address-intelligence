#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulk address workflow script.

This utility reads addresses from an Excel sheet, uploads consignments for each
address, fetches the latest CN details, triggers the validator, and writes the
resulting confidence data back to the workbook.
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables - STRICTLY from backend directory only
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, '.env')
if os.path.exists(env_path):
    # Use override=True to force .env file values to take precedence over system env vars
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️  Warning: {env_path} not found. Using system environment variables only.")

# GEMINI API Key from environment variable (now forced from .env file)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    # Mask the API key for security in logs
    print("✅ GEMINI_API_KEY loaded from .env file")
else:
    print("⚠️  Warning: GEMINI_API_KEY not found in .env file. LLM validation may fail.")

DEFAULT_ADDRESS_COLUMN = os.getenv("ADDRESS_COLUMN", "Address ")
DEFAULT_START_CN = os.getenv("START_CONSIGNMENT", "DEMO01005")
DEFAULT_EXCEL_PATH = Path(os.getenv("ADDRESS_EXCEL_PATH", "backend/address.xlsx"))

UPLOAD_URL = os.getenv(
    "SHIPSY_UPLOAD_URL",
    "https://demodashboardapi.shipsy.io/api/client/integration/consignment/upload/softdata/v2",
)
FETCH_URL = os.getenv("VALIDATOR_FETCH_URL", "http://localhost:5000/api/fetch-cn-details")
VALIDATE_URL = os.getenv("VALIDATOR_VALIDATE_URL", "http://localhost:5000/api/validate-single")
UPLOAD_AUTH = os.getenv(
    "SHIPSY_BASIC_AUTH",
    "Basic YmNmZDdlZWJmNzdiMmQ4NDJlNzVjMDA1NzI3OGY4Og==",
)

DEFAULT_CONSIGNEE_NAME = os.getenv("DEFAULT_CONSIGNEE_NAME", "Bala")
DEFAULT_CONSIGNEE_PHONE = os.getenv("DEFAULT_CONSIGNEE_PHONE", "+919952602775")
DEFAULT_DESCRIPTION = os.getenv("DEFAULT_DESCRIPTION", "Bulk address validation upload")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))

RESULT_CONFIDENCE_COL = os.getenv("CONFIDENCE_COL", "confidence_level")
RESULT_ISSUES_COL = os.getenv("ISSUES_COL", "issues")
RESULT_LAT_COL = os.getenv("LAT_COL", "llm_latitude")
RESULT_LON_COL = os.getenv("LON_COL", "llm_longitude")
RESULT_CN_COL = os.getenv("CN_COL", "consignment_number")


def _base_upload_payload() -> Dict[str, Any]:
    """Return a fresh copy of the reference upload payload."""
    return {
        "service_type_id": "Alcohol",
        "customer_code": "Aramex",
        "reference_number": "",
        "__is_rural": False,
        "declared_value": "22.0000",
        "hub_code": "Sydney",
        "action_type": "pickup",
        "description": DEFAULT_DESCRIPTION,
        "verify_otp_on_delivery": True,
        "origin_details": {
            "name": "Aramex",
            "phone": "7382451923",
            "address_line_1": "2800, C Block, Sushant Lok",
            "pincode": "122002",
            "city": "Gurgaon",
            "country": "India",
            "latitude": "",
            "longitude": "",
        },
        "destination_details": {
            "name": DEFAULT_CONSIGNEE_NAME,
            "phone": DEFAULT_CONSIGNEE_PHONE,
            "address_line_1": "",
            "pincode": "",
            "city": "",
            "country": "",
            "latitude": "",
            "longitude": "",
        },
    }


def _format_consignment_sequence(start: str) -> Iterator[str]:
    """
    Yield sequential consignment numbers preserving the numeric width.

    Example: start='DEMO01005' -> DEMO01005, DEMO01006, ...
    """
    match = re.match(r"([A-Za-z]+)(\d+)$", start.strip())
    if not match:
        raise ValueError(
            f"Unable to parse start consignment number '{start}'. Expected prefix+digits."
        )

    prefix, numeric = match.groups()
    width = len(numeric)
    current = int(numeric)

    while True:
        yield f"{prefix}{current:0{width}d}"
        current += 1


def build_upload_payload(address_line_1: str, consignment_number: str) -> Dict[str, Any]:
    """Populate the upload payload for the provided address."""
    payload = _base_upload_payload()
    payload["reference_number"] = consignment_number
    payload["description"] = f"{DEFAULT_DESCRIPTION} ({consignment_number})"
    payload["destination_details"]["address_line_1"] = address_line_1
    return payload


def upload_consignment(session: requests.Session, payload: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    """Send the consignment upload request."""
    if dry_run:
        print("Dry run: skipping upload")
        return {}

    headers = {
        "Authorization": UPLOAD_AUTH,
        "Content-Type": "application/json",
    }

    response = session.post(
        UPLOAD_URL,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def fetch_cn_details(
    session: requests.Session,
    consignment_number: str,
    retries: int = 3,
    retry_delay: float = 2.0,
) -> Dict[str, Any]:
    """Fetch CN details via the backend helper endpoint."""
    payload = {"consignment_number": consignment_number}

    for attempt in range(1, retries + 1):
        response = session.post(
            FETCH_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        if response.ok:
            result = response.json()
            if result.get("success"):
                return result

        print(
            f"Fetch attempt {attempt}/{retries} failed for {consignment_number}: "
            f"{response.status_code} {response.text}"
        )
        if attempt < retries:
            time.sleep(retry_delay)

    raise RuntimeError(f"Unable to fetch CN details for {consignment_number} after {retries} attempts")


def validate_single(
    session: requests.Session,
    address: str,
    consignment_number: str,
    cn_details: Dict[str, Any],
) -> Dict[str, Any]:
    """Trigger the validator for a CN."""
    payload = {
        "address": address,
        "contact_number": cn_details.get("contact_number") or DEFAULT_CONSIGNEE_PHONE,
        "validation_mode": "llm",
        "consignment_number": consignment_number,
        "cn_details": cn_details,
        "gemini_api_key": GEMINI_API_KEY,  # Pass the API key from environment variable
    }

    # Print which API key we are using when calling LLM (masked for security)
    api_key_display = f"{GEMINI_API_KEY[:8]}..." if GEMINI_API_KEY and len(GEMINI_API_KEY) > 8 else "Not set"
    print(f"\n🔑 Calling LLM with API Key: {api_key_display}")
    print(f"📤 Making validation request to: {VALIDATE_URL}")

    response = session.post(
        VALIDATE_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    
    print(f"📥 Response status: {response.status_code}")
    response.raise_for_status()
    return response.json()


def ensure_result_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee the result columns exist so we can assign into them."""
    for column in [RESULT_CN_COL, RESULT_CONFIDENCE_COL, RESULT_ISSUES_COL, RESULT_LAT_COL, RESULT_LON_COL]:
        if column not in df.columns:
            df[column] = None
    return df


def process_addresses(
    df: pd.DataFrame,
    address_column: str,
    start_consignment: str,
    limit: Optional[int],
    dry_run: bool,
    pause: float,
) -> pd.DataFrame:
    """Iterate rows, run the API workflow, and store results."""
    session = requests.Session()
    seq = _format_consignment_sequence(start_consignment)

    processed = 0

    for idx, address in df[address_column].items():
        if limit is not None and processed >= limit:
            break

        if pd.isna(address) or not str(address).strip():
            continue

        consignment_number = next(seq)
        address_str = str(address).strip()
        print(f"\n=== Processing row {idx} | CN {consignment_number} ===")
        print(f"Address: {address_str}")

        df.at[idx, RESULT_CN_COL] = consignment_number

        payload = build_upload_payload(address_str, consignment_number)

        try:
            upload_response = upload_consignment(session, copy.deepcopy(payload), dry_run=dry_run)
            if upload_response:
                print(f"Upload response: {upload_response}")

            if dry_run:
                print("Dry run: skipping fetch/validate")
                continue

            cn_details = fetch_cn_details(session, consignment_number)
            address_for_validation = cn_details.get("full_address") or cn_details.get("consignee_address") or address_str
            validation_result = validate_single(
                session,
                address=address_for_validation,
                consignment_number=consignment_number,
                cn_details=cn_details,
            )

            coords = validation_result.get("coordinates") or {}
            df.at[idx, RESULT_CONFIDENCE_COL] = validation_result.get("confidence_level")
            issues_text = " | ".join(validation_result.get("issues") or [])
            df.at[idx, RESULT_ISSUES_COL] = issues_text
            df.at[idx, RESULT_LAT_COL] = coords.get("latitude")
            df.at[idx, RESULT_LON_COL] = coords.get("longitude")

            print(
                f"Stored results - Level: {validation_result.get('confidence_level')} | "
                f"Score: {validation_result.get('confidence_score')} | "
                f"Issues: {issues_text or 'None'}"
            )

        except Exception as exc:
            print(f"Error while processing row {idx}: {exc}")
            df.at[idx, RESULT_ISSUES_COL] = f"Error: {exc}"
        finally:
            processed += 1
            if pause and not dry_run:
                time.sleep(pause)

    return df


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk address workflow runner")
    parser.add_argument(
        "--excel-path",
        default=str(DEFAULT_EXCEL_PATH),
        help=f"Path to the Excel file (default: {DEFAULT_EXCEL_PATH})",
    )
    parser.add_argument(
        "--address-column",
        default=DEFAULT_ADDRESS_COLUMN,
        help=f"Column to read addresses from (default: '{DEFAULT_ADDRESS_COLUMN}')",
    )
    parser.add_argument(
        "--start-consignment",
        default=DEFAULT_START_CN,
        help=f"Starting consignment/reference number (default: {DEFAULT_START_CN})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process the first N rows (after skipping blanks)",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=float(os.getenv("REQUEST_PAUSE", "0")),
        help="Seconds to sleep between rows to avoid rate limits",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip HTTP calls and only show what would happen",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    df = pd.read_excel(excel_path)
    if args.address_column not in df.columns:
        raise KeyError(
            f"Column '{args.address_column}' does not exist. Available columns: {list(df.columns)}"
        )

    df = ensure_result_columns(df)
    updated_df = process_addresses(
        df,
        address_column=args.address_column,
        start_consignment=args.start_consignment,
        limit=args.limit,
        dry_run=args.dry_run,
        pause=args.pause,
    )

    if args.dry_run:
        print("Dry run complete. Workbook not modified.")
        return

    updated_df.to_excel(excel_path, index=False)
    print(f"\n✅ Updated workbook saved to {excel_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
