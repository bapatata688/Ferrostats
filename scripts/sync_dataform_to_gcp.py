#!/usr/bin/env python3
"""
FERROSTATS: SYNC LOCAL DATAFORM SQLX FILES TO GCP DATAFORM WORKSPACE
Uploads all files under `dataform/` to the Google Cloud Dataform workspace
`projects/ferrostats/locations/us-central1/repositories/ferrostats-pipeline/workspaces/main-workspace`
and removes any deprecated Spanish Gold `.sqlx` definitions.
"""
import base64
import json
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ferrostats")
LOCATION = "us-central1"
REPO = "ferrostats-pipeline"
WORKSPACE = "main-workspace"

GCLOUD_CMD = os.path.expandvars(r"%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd")
if not os.path.exists(GCLOUD_CMD):
    GCLOUD_CMD = "gcloud"


def get_token() -> str:
    res = subprocess.run([GCLOUD_CMD, "auth", "print-access-token"], capture_output=True, text=True, check=True)
    return res.stdout.strip()


def write_workspace_file(token: str, relative_path: str, content_bytes: bytes):
    ws_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/repositories/{REPO}/workspaces/{WORKSPACE}"
    url = f"https://dataform.googleapis.com/v1beta1/{ws_path}:writeFile"
    payload = {
        "path": relative_path,
        "contents": base64.b64encode(content_bytes).decode("ascii")
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
            print(f"[OK] Uploaded to Dataform Workspace: {relative_path}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Uploading {relative_path}: {e.code} -> {e.read().decode('utf-8')}")
        raise


def remove_workspace_file(token: str, relative_path: str):
    ws_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/repositories/{REPO}/workspaces/{WORKSPACE}"
    url = f"https://dataform.googleapis.com/v1beta1/{ws_path}:removeFile"
    payload = {"path": relative_path}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
            print(f"[OK] Removed legacy file from Dataform Workspace: {relative_path}")
    except urllib.error.HTTPError as e:
        if e.code == 404 or e.code == 400:
            print(f"[SKIP] Legacy file already absent in Dataform Workspace: {relative_path}")
        else:
            print(f"[WARN] Could not remove {relative_path}: {e.code}")


def main():
    base_dir = Path(__file__).resolve().parent.parent / "dataform"
    token = get_token()

    # Remove deprecated Spanish Gold SQLX files from remote workspace if present
    legacy_files = [
        "definitions/gold/dim_productos.sqlx",
        "definitions/gold/fct_ventas_diarias.sqlx",
        "definitions/gold/mart_inventario_pareto_abc.sqlx",
    ]
    for old_path in legacy_files:
        remove_workspace_file(token, old_path)

    for file_path in sorted(base_dir.rglob("*")):
        if file_path.is_file():
            rel_path = file_path.relative_to(base_dir).as_posix()
            write_workspace_file(token, rel_path, file_path.read_bytes())

    print("=================================================================")
    print("  [SUCCESS] ALL DATAFORM SQLX FILES SYNCHRONIZED TO GCP!")
    print("=================================================================")


if __name__ == "__main__":
    main()
