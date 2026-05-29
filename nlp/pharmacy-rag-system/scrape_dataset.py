"""
Pharmindex scraper v3
- Pagination: click "Next" (DataTables AJAX)
- Leaflet: click tab "Ulotka przylekowa" → AJAX → click each section → collect
- JSON: ulotka jako tablica sekcji [{tytul, tresc}]

Requirements:
    pip install selenium webdriver-manager beautifulsoup4

Usage:
    python pharmindex_scraper.py
"""

import json
import time
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementNotInteractableException, StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

# ╔══════════════════════════════════════════════════════════════════╗
# ║                        CONFIGURATION                            ║
# ╚══════════════════════════════════════════════════════════════════╝
TARGET_DRUG_COUNT       = 3000    # how many drugs to collect
HEADLESS                = True  # True = no Chrome window
AJAX_DELAY              = 0.5   # sec to wait for leaflet to load via AJAX
SECTION_DELAY           = 0.1   # sec after expanding each section
PAGE_DELAY              = 2.5   # sec after page change
OUTPUT_FILE             = "pharmacy_dataset_rag_v2.json"
# ══════════════════════════════════════════════════════════════════


# ─── DRIVER ──────────────────────────────────────────────────────

def build_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-notifications")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )


# ─── HELPERS ─────────────────────────────────────────────────────

def js_click(driver, element):
    """Click via JS – bypasses visibility and overlay issues."""
    driver.execute_script("arguments[0].click();", element)


def accept_gdpr(driver):
    try:
        btn = WebDriverWait(driver, 7).until(
            EC.element_to_be_clickable((By.ID, "cookies-btn-primary"))
        )
        btn.click()
        print("GDPR accepted.")
        time.sleep(0.6)
    except TimeoutException:
        pass


def wait_for_table(driver, timeout=25):
    """Waits until DataTables loads rows and spinner disappears."""
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#packages table tbody tr")
        )
    )
    try:
        WebDriverWait(driver, 6).until(
            EC.invisibility_of_element_located((By.ID, "dt_processing"))
        )
    except TimeoutException:
        pass
    time.sleep(PAGE_DELAY)


# ─── LEAFLET ─────────────────────────────────────────────────────

def fetch_leaflet(driver, row_id: str) -> list[dict]:
    """
    For a single row (drug):
      1. Clicks the "Ulotka przylekowa" tab
      2. Waits for AJAX to load
      3. Clicks each .box-7 .name section to expand it
      4. Collects [{tytul, tresc}, ...] for each section

    Returns an empty list if something goes wrong.
    """
    leaflet_sections = []

    try:
        # ── 1. Find and click the "Ulotka przylekowa" tab ─────────────────
        tab_selector = f"#pils-{row_id}"
        try:
            tab = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, tab_selector))
            )
        except TimeoutException:
            print(f"      [!] No leaflet tab for ID={row_id}")
            return []

        # Scroll to row to make it visible
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", tab
        )
        time.sleep(0.3)
        js_click(driver, tab)

        # ── 2. Wait for AJAX to load ───────────────────────────────────────
        # After clicking the tab, .cont-boxes appears with content
        # We look for .boxes-7 inside this specific row
        # NOTE: Row IDs are numbers (e.g. "12313") – CSS #12313 is illegal.
        # Using attribute selector [id="12313"] instead of #12313.
        container_selector = (
            f'#packages table tbody tr[id="{row_id}"] .cont-boxes .boxes-7, '
            f'#packages table tbody tr[id="{row_id}"] .cont-boxes .content-padding-1'
        )
        try:
            WebDriverWait(driver, AJAX_DELAY + 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, container_selector))
            )
        except TimeoutException:
            # Drug may have no leaflet – OK
            pass

        time.sleep(AJAX_DELAY)

        # ── 3. Find row in DOM via XPath (safe for numeric IDs) ───────────
        try:
            row_el = driver.find_element(
                By.XPATH, f'//table[@id="dt"]//tbody/tr[@id="{row_id}"]'
            )
        except NoSuchElementException:
            # Fallback: CSS attribute
            try:
                row_el = driver.find_element(
                    By.CSS_SELECTOR, f'tr[id="{row_id}"]'
                )
            except NoSuchElementException:
                return []

        # Section headers to expand: .box-7 .name (clickable header)
        headers = row_el.find_elements(
            By.CSS_SELECTOR, ".box-7 .name"
        )

        for header in headers:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", header
                )
                time.sleep(0.15)
                js_click(driver, header)
                time.sleep(SECTION_DELAY)
            except (StaleElementReferenceException, Exception):
                pass  # section already expanded or error – continue

        # ── 4. Collect text after all sections are expanded ───────────────
        row_html = row_el.get_attribute("outerHTML")
        soup = BeautifulSoup(row_html, "html.parser")

        for box7 in soup.select(".box-7"):
            header_el = box7.select_one(".name span")
            desc_el   = box7.select_one(".description")

            tytul = header_el.get_text(separator=" ", strip=True) if header_el else ""
            tresc = desc_el.get_text(separator=" ", strip=True)   if desc_el   else ""

            # Clean up excessive whitespace in content
            tresc = " ".join(tresc.split())

            if tytul or tresc:
                leaflet_sections.append({
                    "tytul": tytul,
                    "tresc": tresc,
                })

        # Fallback: if .boxes-7 is empty, collect all text from container
        if not leaflet_sections:
            container_bs = soup.select_one(".cont-boxes, .content-padding-1")
            if container_bs:
                text = " ".join(container_bs.get_text(separator=" ").split())
                if text:
                    leaflet_sections.append({"tytul": "Ulotka", "tresc": text})

    except Exception as e:
        print(f"      [!] Error fetching leaflet ID={row_id}: {e}")

    return leaflet_sections


# ─── ROW PARSING ─────────────────────────────────────────────────

def extract_row_data(row_soup: BeautifulSoup) -> dict | None:
    """Extracts basic drug metadata from a BeautifulSoup row."""
    try:
        # Row ID (needed for tab clicking)
        row_id = row_soup.get("id", "")
        if not row_id:
            return None

        # Trade name
        name_el = row_soup.select_one(".txt-1 a")
        name = name_el.get_text(strip=True) if name_el else "Brak nazwy"

        # Active substance
        substance_el = row_soup.select_one(".txt-2")
        substance = (
            substance_el.get_text(separator=", ", strip=True)
            if substance_el else "Brak substancji"
        )

        # Form / dose / packaging
        details_el = row_soup.select_one(".box-5-3")
        if details_el:
            details = " | ".join(
                ln.strip()
                for ln in details_el.get_text(separator="\n").splitlines()
                if ln.strip()
            )
        else:
            details = "Brak szczegółów"

        # Prescription status (Rp / OTC / Lz etc.)
        prescription_els = row_soup.select(".box-5-5 .xic-txt")
        prescription_parts = [el.get_text(strip=True) for el in prescription_els if el.get_text(strip=True)]
        prescription = " | ".join(prescription_parts)

        return {
            "row_id":      row_id,
            "nazwa":       name,
            "substancja":  substance,
            "szczegoly":   details,
            "recepta":     prescription,
        }
    except Exception as e:
        print(f"  [!] Error parsing row: {e}")
        return None


def build_rag_chunk(data: dict, sections: list[dict]) -> str:
    """Builds a single long string for RAG embedding."""
    lines = [
        f"NAZWA HANDLOWA: {data['nazwa']}",
        f"SUBSTANCJA CZYNNA: {data['substancja']}",
        f"SPECYFIKACJA (Postać, dawka, opakowanie): {data['szczegoly']}",
        f"STATUS: {data['recepta']}",
        "",
        "=== ULOTKA ===",
    ]
    for s in sections:
        if s["tytul"]:
            lines.append(f"\n--- {s['tytul']} ---")
        lines.append(s["tresc"])

    return "\n".join(lines).strip()


# ─── PAGINATION ───────────────────────────────────────────────────

def click_next(driver) -> bool:
    """Clicks 'Next'. Returns False on last page."""
    try:
        btn = driver.find_element(By.ID, "dt_next")
        if "disabled" in (btn.get_attribute("class") or ""):
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.3)
        js_click(driver, btn)
        return True
    except (NoSuchElementException, ElementNotInteractableException) as e:
        print(f"  [!] Cannot click 'Next': {e}")
        return False


def wait_for_new_page(driver, old_first_tr):
    """Waits until DataTables swaps the DOM after clicking Next."""
    try:
        WebDriverWait(driver, 15).until(
            EC.staleness_of(old_first_tr)
        )
    except (TimeoutException, StaleElementReferenceException):
        pass
    wait_for_table(driver)


# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    print(f"   Target: {TARGET_DRUG_COUNT} drugs")
    print(f"   Mode: {'headless' if HEADLESS else 'Chrome window'}")

    driver = build_driver()
    database: list[dict] = []

    try:
        driver.get("https://pharmindex.pl/listalekow")
        accept_gdpr(driver)
        wait_for_table(driver)

        page_number = 1

        while len(database) < TARGET_DRUG_COUNT:
            print(f"\n{'═'*55}")
            print(f"Page {page_number} | Collected: {len(database)}/{TARGET_DRUG_COUNT}")
            print(f"{'═'*55}")

            # ── Fetch row list from current HTML ──────────────────────────
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows_soup = soup.select("#packages table tbody tr")

            if not rows_soup:
                print("No rows on page.")
                break

            # Limit to how many we still need
            remaining = TARGET_DRUG_COUNT - len(database)
            rows_soup = rows_soup[:remaining]

            # ── For each drug: basic data + leaflet ───────────────────────
            for i, row_bs in enumerate(rows_soup):
                data = extract_row_data(row_bs)
                if not data:
                    continue

                row_id = data["row_id"]
                print(f"  [{len(database)+1:>4}] {data['nazwa'][:55]:<55} ID={row_id}")

                # Fetch leaflet (tab click + section clicks)
                sections = fetch_leaflet(driver, row_id)

                if sections:
                    print(f"         ↳ {len(sections)} leaflet sections")
                else:
                    print(f"         ↳ no leaflet")
                    sections = []

                chunk = build_rag_chunk(data, sections)

                database.append({
                    "id":                len(database) + 1,
                    "nazwa_handlowa":    data["nazwa"],
                    "substancja_czynna": data["substancja"],
                    "specyfikacja":      data["szczegoly"],
                    "status_recepty":    data["recepta"],
                    "ulotka_sekcje":     sections,          # ← tablica sekcji
                    "rag_input_chunk":   chunk,              # ← pełny tekst do RAG
                })

                if len(database) >= TARGET_DRUG_COUNT:
                    break

            # ── Partial save per page (safety) ────────────────────────────
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(database, f, indent=2, ensure_ascii=False)
            print(f"\n Partial save: {len(database)} drugs -> {OUTPUT_FILE}")

            if len(database) >= TARGET_DRUG_COUNT:
                break

            # ── Go to next page ───────────────────────────────────────────
            try:
                old_tr = driver.find_elements(
                    By.CSS_SELECTOR, "#packages table tbody tr"
                )[0]
            except IndexError:
                old_tr = None

            if not click_next(driver):
                print("Last page – stopping.")
                break

            if old_tr:
                wait_for_new_page(driver, old_tr)
            else:
                wait_for_table(driver)

            page_number += 1

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        traceback.print_exc()

    finally:
        driver.quit()

    # ── Final save ────────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=2, ensure_ascii=False)

    print(f"\n{'═'*55}")
    print(f"DONE! Saved {len(database)} drugs → {OUTPUT_FILE}")

    if database:
        print(f"\nExample structure of first drug:")
        print(f"  nazwa_handlowa : {database[0]['nazwa_handlowa']}")
        print(f"  substancja     : {database[0]['substancja_czynna']}")
        print(f"  ulotka_sekcje  : {len(database[0]['ulotka_sekcje'])} sections")
        for s in database[0]["ulotka_sekcje"]:
            print(f"    • {s['tytul'][:70]}")


if __name__ == "__main__":
    main()