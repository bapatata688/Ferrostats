import os
import sys
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from scripts.deploy_dataform_models import get_access_token

BASE_DIR = Path(__file__).resolve().parent.parent
DATAFORM_DIR = BASE_DIR / "dataform"
PROJECT_ID = "ferrostats"
LOCATION = "us-central1"
REPO_ID = "ferrostats-pipeline"
WORKSPACE_ID = "main-workspace"

def main():
    print("=" * 65)
    print("  SINCRONIZANDO ARCHIVOS SQLX A GOOGLE CLOUD DATAFORM CONSOLE")
    print("=" * 65)
    token = get_access_token()

    workspace_full = f"projects/{PROJECT_ID}/locations/{LOCATION}/repositories/{REPO_ID}/workspaces/{WORKSPACE_ID}"

    # Recorrer todos los archivos dentro de dataform/
    files_to_sync = []
    for root, dirs, files in os.walk(DATAFORM_DIR):
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(DATAFORM_DIR).as_posix()
            files_to_sync.append((rel_path, full_path))

    print(f"Total de archivos a subir a GCP Dataform: {len(files_to_sync)}\n")

    for rel_path, full_path in files_to_sync:
        with open(full_path, "rb") as fp:
            content_bytes = fp.read()
        
        b64_content = base64.b64encode(content_bytes).decode("ascii")

        url = f"https://dataform.googleapis.com/v1beta1/{workspace_full}:writeFile"
        payload = {
            "path": rel_path,
            "contents": b64_content
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                print(f"[OK] Subido a Dataform: {rel_path}")
        except urllib.error.HTTPError as err:
            err_text = err.read().decode("utf-8")
            print(f"[ERR] Fallo al subir {rel_path} ({err.code}): {err_text}")

    print("\n" + "=" * 65)
    print("  ¡TODOS LOS ARCHIVOS SQLX Y CONFIGURACIONES SUBIDOS A DATAFORM!")
    print(f"  Repositorio: {REPO_ID}")
    print(f"  Espacio de trabajo: {WORKSPACE_ID}")
    print(f"  Consola Web: https://console.cloud.google.com/bigquery/dataform/locations/{LOCATION}/repositories/{REPO_ID}/workspaces/{WORKSPACE_ID}?project={PROJECT_ID}")
    print("=" * 65)

if __name__ == "__main__":
    main()
