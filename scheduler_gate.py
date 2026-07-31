#!/usr/bin/env python3
"""
Decide si corresponde ejecutar la revisión de Flexit ahora mismo.

Reglas:
- Solo puede correr entre HORA_INICIO y HORA_FIN (hora de Chile continental).
- Entre una revisión y la siguiente debe pasar un intervalo aleatorio de
  entre MIN_INTERVALO y MAX_INTERVALO minutos (no siempre el mismo, para
  no dejar un patrón de tráfico perfectamente regular).

Este script no necesita playwright ni dependencias externas, así que las
veces que decide "todavía no toca" son rapidísimas y casi no consumen
minutos de GitHub Actions.
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

STATE = Path(__file__).parent / "next_run.json"
TZ = ZoneInfo("America/Santiago")

HORA_INICIO = 8   # 08:00
HORA_FIN = 21     # 21:00 (9 pm), exclusivo
MIN_INTERVALO_MIN = 13
MAX_INTERVALO_MIN = 17


def main():
    now = datetime.now(TZ)
    should_run = False
    reason = ""

    if not (HORA_INICIO <= now.hour < HORA_FIN):
        reason = (f"Fuera de horario permitido ({HORA_INICIO:02d}:00–{HORA_FIN:02d}:00). "
                  f"Hora actual en Chile: {now.strftime('%H:%M')}")
    else:
        next_check_at = None
        if STATE.exists():
            try:
                data = json.loads(STATE.read_text())
                next_check_at = datetime.fromisoformat(data["next_check_at"])
            except Exception:
                next_check_at = None

        if next_check_at is None or now >= next_check_at:
            should_run = True
        else:
            reason = f"Aún no toca revisar. Próxima revisión: {next_check_at.strftime('%H:%M:%S')}"

    if should_run:
        intervalo = random.uniform(MIN_INTERVALO_MIN, MAX_INTERVALO_MIN)
        proximo = now + timedelta(minutes=intervalo)
        STATE.write_text(json.dumps({"next_check_at": proximo.isoformat()}, indent=2))
        print(f"Corresponde revisar ahora. Próxima revisión ~{proximo.strftime('%H:%M:%S')} "
              f"(en {intervalo:.1f} min).")
    else:
        print(reason)

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"should_run={'true' if should_run else 'false'}\n")


if __name__ == "__main__":
    main()
