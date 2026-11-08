"""Inicia a API real, valida /health por HTTP e encerra o processo."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[2]
PORT = 8765


def main() -> None:
    # Ignora proxies apenas na chamada HTTP local desta verificacao.
    http = build_opener(ProxyHandler({}))
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(PORT),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"API encerrou com codigo {process.returncode}.")
                try:
                    with http.open(f"http://127.0.0.1:{PORT}/health", timeout=2) as response:
                        payload = json.load(response)
                        if response.status != 200 or payload != {
                            "status": "ok",
                            "problemas_de_configuracao": [],
                        }:
                            raise RuntimeError(f"/health reprovado: {payload}")
                    print("/health aprovado: HTTP 200, status=ok e nenhuma pendencia.")
                    return
                except (URLError, TimeoutError):
                    time.sleep(1)
            raise TimeoutError("API nao respondeu a /health em ate 60 segundos.")
        except Exception:
            log.seek(0)
            print(log.read()[-12000:], file=sys.stderr)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    main()
