#!/usr/bin/env python3
"""
Flexit Watcher
--------------
Revisa https://www.flexit.cl/trabajar, selecciona la región de Arica y
Parinacota, y envía una notificación push (via ntfy.sh) cuando aparece
una oferta nueva que no se había visto antes.

Estado: guarda un archivo seen_jobs.json con un "hash" de cada oferta ya
notificada, para no repetir avisos.

Variables de entorno:
  NTFY_TOPIC   -> tema de ntfy.sh al que se envía la notificación (obligatorio)
  REGION_TEXT  -> texto de la región a buscar (por defecto "Arica y Parinacota")
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

URL = "https://www.flexit.cl/trabajar"
STATE_FILE = Path(__file__).parent / "seen_jobs.json"
DEBUG_SCREENSHOT = Path(__file__).parent / "debug.png"
DEBUG_TEXT = Path(__file__).parent / "debug_page_text.txt"

REGION_TEXT = os.environ.get("REGION_TEXT", "Arica y Parinacota")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

# Patrón que reconoce cada tarjeta de oferta a partir del texto visible de la
# página, basado en la estructura observada: Titulo / $$$ / Empresa Lugar /
# fecha - fecha / hora - hora
JOB_PATTERN = re.compile(
    r"(?P<title>[^\n$]{3,80})\n\${1,3}\n"
    r"(?P<empresa>[^\n]{3,80})\n"
    r"(?P<fechas>\d{2}/\d{2}/\d{2}\s*-\s*\d{2}/\d{2}/\d{2})\n"
    r"(?P<horas>\d{2}:\d{2}\s*-\s*\d{2}:\d{2})",
    re.MULTILINE,
)


def load_seen() -> set:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_seen(seen: set) -> None:
    STATE_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2))


def parse_start_date(fechas: str):
    """Convierte 'dd/mm/aa - dd/mm/aa' en un datetime usando la primera fecha.
    Devuelve None si no se puede interpretar."""
    try:
        primera = fechas.split("-")[0].strip()
        return datetime.strptime(primera, "%d/%m/%y")
    except Exception:
        return None


def job_id(title: str, empresa: str, fechas: str, horas: str) -> str:
    raw = f"{title.strip()}|{empresa.strip()}|{fechas.strip()}|{horas.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def click_search_button(page) -> bool:
    """Intenta apretar el botón de la lupa/buscar para aplicar el filtro de
    región. Prueba varias formas de encontrarlo porque no conocemos el
    markup exacto del sitio."""

    candidatos = [
        page.get_by_role("button", name=re.compile("buscar", re.IGNORECASE)),
        page.locator("button[aria-label*='buscar' i]"),
        page.locator("button[aria-label*='search' i]"),
        page.locator("[class*='search' i][role='button']"),
        page.locator("button:has(svg[class*='search' i])"),
    ]
    for cand in candidatos:
        try:
            if cand.count() > 0:
                cand.first.click(timeout=3000)
                return True
        except Exception:
            continue

    # Último recurso: presionar Enter, por si el buscador envía el
    # formulario con el teclado.
    try:
        page.keyboard.press("Enter")
        return True
    except Exception:
        return False


def select_region(page) -> bool:
    """Intenta seleccionar la región en el buscador de ofertas.
    Prueba primero un <select> nativo, y si no existe, un dropdown custom."""

    # 1) <select> nativo
    for sel in page.query_selector_all("select"):
        for opt in sel.query_selector_all("option"):
            text = (opt.inner_text() or "").lower()
            if "arica" in text and "parinacota" in text:
                value = opt.get_attribute("value")
                try:
                    sel.select_option(value=value)
                    return True
                except Exception:
                    pass

    # 2) Dropdown personalizado: buscar el control que dice
    #    "Selecciona una región" o similar y hacer click, luego click en la opción
    triggers = page.get_by_text(re.compile("selecciona.*regi", re.IGNORECASE))
    try:
        count = triggers.count()
    except Exception:
        count = 0

    for i in range(count):
        try:
            triggers.nth(i).click(timeout=3000)
            page.wait_for_timeout(600)
            option = page.get_by_text(re.compile(re.escape(REGION_TEXT), re.IGNORECASE))
            if option.count() > 0:
                option.first.click(timeout=3000)
                return True
        except Exception:
            continue

    return False


def fetch_jobs() -> list[dict]:
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="es-CL")
        page.goto(URL, wait_until="networkidle", timeout=60000)

        selected = select_region(page)
        if selected:
            page.wait_for_timeout(400)
            click_search_button(page)
        page.wait_for_timeout(2500)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        body_text = page.inner_text("body")

        # Guarda evidencia de depuración siempre (útil si algo falla)
        try:
            page.screenshot(path=str(DEBUG_SCREENSHOT), full_page=True)
        except Exception:
            pass
        DEBUG_TEXT.write_text(body_text, encoding="utf-8")

        browser.close()

        if not selected:
            print("ADVERTENCIA: no se pudo seleccionar la región automáticamente. "
                  "Revisa debug.png y debug_page_text.txt", file=sys.stderr)

        for m in JOB_PATTERN.finditer(body_text):
            jobs.append({
                "title": m.group("title").strip(),
                "empresa": m.group("empresa").strip(),
                "fechas": m.group("fechas").strip(),
                "horas": m.group("horas").strip(),
            })

    return jobs


def notify(job: dict) -> None:
    if not NTFY_TOPIC:
        print("NTFY_TOPIC no configurado, no se puede notificar:", job)
        return

    title = "📢 Nueva oferta en tu región"
    message = f"{job['title']}\n{job['empresa']}\n📅 {job['fechas']}  🕐 {job['horas']}"

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Click": URL,
                "Tags": "briefcase",
                "Priority": "high",
            },
            timeout=10,
        )
        print("Notificación enviada:", job)
    except Exception as e:
        print("Error enviando notificación:", e, file=sys.stderr)


def notify_status(total: int, latest_job: dict | None) -> None:
    if not NTFY_TOPIC:
        return

    if latest_job:
        cuerpo = (
            f"{total} oferta(s) visibles ahora.\n"
            f"Más reciente: {latest_job['title']} — {latest_job['empresa']}\n"
            f"📅 {latest_job['fechas']}"
        )
    else:
        cuerpo = "0 ofertas visibles ahora en tu región."

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=cuerpo.encode("utf-8"),
            headers={
                "Title": "✅ Verificación Flexit Watcher".encode("utf-8"),
                "Click": URL,
                "Tags": "mag",
                "Priority": "default",
            },
            timeout=10,
        )
        print("Notificación de estado enviada.")
    except Exception as e:
        print("Error enviando notificación de estado:", e, file=sys.stderr)


def main():
    seen = load_seen()
    jobs = fetch_jobs()

    print(f"Ofertas encontradas en esta pasada: {len(jobs)}")

    new_count = 0
    for job in jobs:
        jid = job_id(job["title"], job["empresa"], job["fechas"], job["horas"])
        if jid not in seen:
            notify(job)
            seen.add(jid)
            new_count += 1

    save_seen(seen)
    print(f"Ofertas nuevas notificadas: {new_count}")

    # Notificación de estado: la fecha más reciente encontrada, para poder
    # verificar de un vistazo que el script está leyendo datos actuales.
    latest_job = None
    latest_date = None
    for job in jobs:
        d = parse_start_date(job["fechas"])
        if d and (latest_date is None or d > latest_date):
            latest_date = d
            latest_job = job

    notify_status(len(jobs), latest_job)


if __name__ == "__main__":
    main()
