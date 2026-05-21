"""
Pharmindex scraper v3
- Paginacja: klik "Następna" (DataTables AJAX)
- Ulotka: klik zakładki "Ulotka przylekowa" → AJAX → klik każdej sekcji → zbierz
- JSON: ulotka jako tablica sekcji [{tytul, tresc}]

Wymagania:
    pip install selenium webdriver-manager beautifulsoup4

Uruchomienie:
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
# ║                        KONFIGURACJA                             ║
# ╚══════════════════════════════════════════════════════════════════╝
DOCELOWA_LICZBA_LEKOW   = 500    # ile leków zebrać
HEADLESS                = False  # True = bez okna Chrome
OPOZNIENIE_AJAX         = 1.0   # sek czekania na załadowanie ulotki przez AJAX
OPOZNIENIE_SEKCJA       = 0.2   # sek po rozwinięciu każdej sekcji
OPOZNIENIE_STRONA       = 2.5   # sek po zmianie strony
PLIK_WYJSCIOWY          = "pharmacy_dataset_rag.json"
# ══════════════════════════════════════════════════════════════════


# ─── DRIVER ──────────────────────────────────────────────────────

def zbuduj_driver() -> webdriver.Chrome:
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
    """Klikaj przez JS – omija problemy z widocznością i nakładkami."""
    driver.execute_script("arguments[0].click();", element)


def akceptuj_rodo(driver):
    try:
        btn = WebDriverWait(driver, 7).until(
            EC.element_to_be_clickable((By.ID, "cookies-btn-primary"))
        )
        btn.click()
        print("✅ RODO zaakceptowane.")
        time.sleep(0.6)
    except TimeoutException:
        pass


def czekaj_na_tabele(driver, timeout=25):
    """Czeka aż DataTables załaduje wiersze i spinner zniknie."""
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
    time.sleep(OPOZNIENIE_STRONA)


# ─── ULOTKA ──────────────────────────────────────────────────────

def pobierz_ulotke(driver, row_id: str) -> list[dict]:
    """
    Dla jednego wiersza (leku):
      1. Klika zakładkę "Ulotka przylekowa"
      2. Czeka na załadowanie AJAX
      3. Klika każdą sekcję .box-7 .name żeby rozwinąć
      4. Zbiera [{tytul, tresc}, ...] dla każdej sekcji

    Zwraca pustą listę jeśli coś pójdzie nie tak.
    """
    sekcje_ulotki = []

    try:
        # ── 1. Znajdź i kliknij zakładkę "Ulotka przylekowa" ──────────────
        zakladka_sel = f"#pils-{row_id}"
        try:
            zakladka = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, zakladka_sel))
            )
        except TimeoutException:
            print(f"      [!] Brak zakładki ulotki dla ID={row_id}")
            return []

        # Scroll do wiersza żeby był widoczny
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", zakladka
        )
        time.sleep(0.3)
        js_click(driver, zakladka)

        # ── 2. Czekaj na załadowanie AJAX ─────────────────────────────────
        # Po kliknięciu zakładki pojawia się .cont-boxes z zawartością
        # Szukamy .boxes-7 wewnątrz tego konkretnego wiersza
        # UWAGA: ID wierszy to liczby (np. "12313") – CSS #12313 jest nielegalny.
        # Używamy atrybutowego selektora [id="12313"] zamiast #12313.
        kontener_sel = (
            f'#packages table tbody tr[id="{row_id}"] .cont-boxes .boxes-7, '
            f'#packages table tbody tr[id="{row_id}"] .cont-boxes .content-padding-1'
        )
        try:
            WebDriverWait(driver, OPOZNIENIE_AJAX + 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, kontener_sel))
            )
        except TimeoutException:
            # Może być lek bez ulotki – OK
            pass

        time.sleep(OPOZNIENIE_AJAX)

        # ── 3. Znajdź wiersz w DOM przez XPath (bezpieczne dla numerycznych ID) ──
        try:
            wiersz_el = driver.find_element(
                By.XPATH, f'//table[@id="dt"]//tbody/tr[@id="{row_id}"]'
            )
        except NoSuchElementException:
            # Fallback: atrybut CSS
            try:
                wiersz_el = driver.find_element(
                    By.CSS_SELECTOR, f'tr[id="{row_id}"]'
                )
            except NoSuchElementException:
                return []

        # Sekcje do rozwinięcia: .box-7 .name (klikalny nagłówek)
        naglowki = wiersz_el.find_elements(
            By.CSS_SELECTOR, ".box-7 .name"
        )

        for naglowek in naglowki:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", naglowek
                )
                time.sleep(0.15)
                js_click(driver, naglowek)
                time.sleep(OPOZNIENIE_SEKCJA)
            except (StaleElementReferenceException, Exception):
                pass  # sekcja już rozwinięta lub błąd – lecimy dalej

        # ── 4. Zbierz tekst po rozwinięciu wszystkich sekcji ──────────────
        html_wiersza = wiersz_el.get_attribute("outerHTML")
        soup = BeautifulSoup(html_wiersza, "html.parser")

        for box7 in soup.select(".box-7"):
            naglowek_el = box7.select_one(".name span")
            opis_el     = box7.select_one(".description")

            tytul = naglowek_el.get_text(separator=" ", strip=True) if naglowek_el else ""
            tresc = opis_el.get_text(separator=" ", strip=True)      if opis_el     else ""

            # Czyścimy nadmiarowe białe znaki w treści
            tresc = " ".join(tresc.split())

            if tytul or tresc:
                sekcje_ulotki.append({
                    "tytul": tytul,
                    "tresc": tresc,
                })

        # Fallback: jeśli .boxes-7 puste, zbierz cały tekst kontenera
        if not sekcje_ulotki:
            kontener_bs = soup.select_one(".cont-boxes, .content-padding-1")
            if kontener_bs:
                tekst = " ".join(kontener_bs.get_text(separator=" ").split())
                if tekst:
                    sekcje_ulotki.append({"tytul": "Ulotka", "tresc": tekst})

    except Exception as e:
        print(f"      [!] Błąd pobierania ulotki ID={row_id}: {e}")

    return sekcje_ulotki


# ─── PARSOWANIE WIERSZA ───────────────────────────────────────────

def wyciagnij_dane_wiersza(wiersz_soup: BeautifulSoup) -> dict | None:
    """Wyciąga podstawowe metadane leku z BeautifulSoup wiersza."""
    try:
        # ID wiersza (potrzebne do klikania zakładki)
        row_id = wiersz_soup.get("id", "")
        if not row_id:
            return None

        # Nazwa handlowa
        nazwa_el = wiersz_soup.select_one(".txt-1 a")
        nazwa = nazwa_el.get_text(strip=True) if nazwa_el else "Brak nazwy"

        # Substancja czynna
        substancja_el = wiersz_soup.select_one(".txt-2")
        substancja = (
            substancja_el.get_text(separator=", ", strip=True)
            if substancja_el else "Brak substancji"
        )

        # Postać / dawka / opakowanie
        szczegoly_el = wiersz_soup.select_one(".box-5-3")
        if szczegoly_el:
            szczegoly = " | ".join(
                ln.strip()
                for ln in szczegoly_el.get_text(separator="\n").splitlines()
                if ln.strip()
            )
        else:
            szczegoly = "Brak szczegółów"

        # Status recepty (Rp / OTC / Lz itd.)
        recepta_els = wiersz_soup.select(".box-5-5 .xic-txt")
        recepta_czesci = [el.get_text(strip=True) for el in recepta_els if el.get_text(strip=True)]
        recepta = " | ".join(recepta_czesci)

        return {
            "row_id":     row_id,
            "nazwa":      nazwa,
            "substancja": substancja,
            "szczegoly":  szczegoly,
            "recepta":    recepta,
        }
    except Exception as e:
        print(f"  [!] Błąd parsowania wiersza: {e}")
        return None


def zbuduj_chunk_rag(dane: dict, sekcje: list[dict]) -> str:
    """Buduje jeden długi string do embedowania w RAG."""
    linie = [
        f"NAZWA HANDLOWA: {dane['nazwa']}",
        f"SUBSTANCJA CZYNNA: {dane['substancja']}",
        f"SPECYFIKACJA (Postać, dawka, opakowanie): {dane['szczegoly']}",
        f"STATUS: {dane['recepta']}",
        "",
        "=== ULOTKA ===",
    ]
    for s in sekcje:
        if s["tytul"]:
            linie.append(f"\n--- {s['tytul']} ---")
        linie.append(s["tresc"])

    return "\n".join(linie).strip()


# ─── PAGINACJA ────────────────────────────────────────────────────

def kliknij_nastepna(driver) -> bool:
    """Klika 'Następna'. Zwraca False gdy ostatnia strona."""
    try:
        btn = driver.find_element(By.ID, "dt_next")
        if "disabled" in (btn.get_attribute("class") or ""):
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.3)
        js_click(driver, btn)
        return True
    except (NoSuchElementException, ElementNotInteractableException) as e:
        print(f"  [!] Nie można kliknąć 'Następna': {e}")
        return False


def czekaj_na_nowa_strone(driver, stare_pierwsze_tr):
    """Czeka aż DataTables podmieni DOM po kliknięciu Następna."""
    try:
        WebDriverWait(driver, 15).until(
            EC.staleness_of(stare_pierwsze_tr)
        )
    except (TimeoutException, StaleElementReferenceException):
        pass
    czekaj_na_tabele(driver)


# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    print(f"🚀 Cel: {DOCELOWA_LICZBA_LEKOW} leków")
    print(f"   Tryb: {'headless' if HEADLESS else 'z oknem Chrome'}")

    driver = zbuduj_driver()
    baza: list[dict] = []

    try:
        driver.get("https://pharmindex.pl/listalekow")
        akceptuj_rodo(driver)
        czekaj_na_tabele(driver)

        numer_strony = 1

        while len(baza) < DOCELOWA_LICZBA_LEKOW:
            print(f"\n{'═'*55}")
            print(f"📄 Strona {numer_strony} | Zebrano: {len(baza)}/{DOCELOWA_LICZBA_LEKOW}")
            print(f"{'═'*55}")

            # ── Pobierz listę wierszy z aktualnego HTML ────────────────────
            soup = BeautifulSoup(driver.page_source, "html.parser")
            wiersze_soup = soup.select("#packages table tbody tr")

            if not wiersze_soup:
                print("⚠️  Brak wierszy na stronie.")
                break

            # Ogranicz do ile jeszcze potrzebujemy
            pozostalo = DOCELOWA_LICZBA_LEKOW - len(baza)
            wiersze_soup = wiersze_soup[:pozostalo]

            # ── Dla każdego leku: dane podstawowe + ulotka ────────────────
            for i, wiersz_bs in enumerate(wiersze_soup):
                dane = wyciagnij_dane_wiersza(wiersz_bs)
                if not dane:
                    continue

                row_id = dane["row_id"]
                print(f"  [{len(baza)+1:>4}] {dane['nazwa'][:55]:<55} ID={row_id}")

                # Pobierz ulotke (klik zakładki + klik sekcji)
                sekcje = pobierz_ulotke(driver, row_id)

                if sekcje:
                    print(f"         ↳ {len(sekcje)} sekcji ulotki")
                else:
                    print(f"         ↳ brak ulotki")
                    sekcje = []

                chunk = zbuduj_chunk_rag(dane, sekcje)

                baza.append({
                    "id":                len(baza) + 1,
                    "nazwa_handlowa":    dane["nazwa"],
                    "substancja_czynna": dane["substancja"],
                    "specyfikacja":      dane["szczegoly"],
                    "status_recepty":    dane["recepta"],
                    "ulotka_sekcje":     sekcje,          # ← tablica sekcji
                    "rag_input_chunk":   chunk,            # ← pełny tekst do RAG
                })

                if len(baza) >= DOCELOWA_LICZBA_LEKOW:
                    break

            # ── Zapis częściowy co stronę (bezpieczeństwo) ────────────────
            with open(PLIK_WYJSCIOWY, "w", encoding="utf-8") as f:
                json.dump(baza, f, indent=2, ensure_ascii=False)
            print(f"\n  💾 Zapisano częściowo: {len(baza)} leków → {PLIK_WYJSCIOWY}")

            if len(baza) >= DOCELOWA_LICZBA_LEKOW:
                break

            # ── Przejdź na następną stronę ────────────────────────────────
            try:
                stare_tr = driver.find_elements(
                    By.CSS_SELECTOR, "#packages table tbody tr"
                )[0]
            except IndexError:
                stare_tr = None

            if not kliknij_nastepna(driver):
                print("ℹ️  Ostatnia strona – kończymy.")
                break

            if stare_tr:
                czekaj_na_nowa_strone(driver, stare_tr)
            else:
                czekaj_na_tabele(driver)

            numer_strony += 1

    except Exception as e:
        print(f"\n🔥 BŁĄD KRYTYCZNY: {e}")
        traceback.print_exc()

    finally:
        driver.quit()

    # ── Końcowy zapis ──────────────────────────────────────────────────────
    with open(PLIK_WYJSCIOWY, "w", encoding="utf-8") as f:
        json.dump(baza, f, indent=2, ensure_ascii=False)

    print(f"\n{'═'*55}")
    print(f"🎉 GOTOWE! Zapisano {len(baza)} leków → {PLIK_WYJSCIOWY}")

    if baza:
        print(f"\nPrzykład struktury pierwszego leku:")
        print(f"  nazwa_handlowa : {baza[0]['nazwa_handlowa']}")
        print(f"  substancja     : {baza[0]['substancja_czynna']}")
        print(f"  ulotka_sekcje  : {len(baza[0]['ulotka_sekcje'])} sekcji")
        for s in baza[0]["ulotka_sekcje"]:
            print(f"    • {s['tytul'][:70]}")


if __name__ == "__main__":
    main()