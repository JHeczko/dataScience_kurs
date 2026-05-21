# Zbuduj system RAG dla apteki

Postępuj zgodnie z (lekko zmodyfikowanym) [notebookiem](https://www.google.com/search?q=./tutorial.ipynb) z przewodników szybkiego startu (quickstarts) Google-Gemini Cookbook.

## Zadanie:

Przygotuj mały zbiór danych zawierający Ulotki dla Pacjenta (PIL – Patient Information Leaflets).

Możesz pobrać je **w języku polskim** na przykład z [pharmindex](https://pharmindex.pl) lub podobnych baz farmaceutycznych. Możesz skopiować i wkleić je ręcznie lub stworzyć webscraper, cokolwiek wolisz.

Odpowiednio zmodyfikuj potok (pipeline) RAG:

1. Użyj modelu `gemini-embedding-001` do wygenerowania embeddingów dokumentów (`task_type="RETRIEVAL_DOCUMENT"`) oraz embeddingów zapytań (`task_type="RETRIEVAL_QUERY"`).
2. Dla danego zapytania wyszukaj (retrieve) niewielką liczbę ulotek (PIL) i wygeneruj odpowiedź (za pomocą dowolnego z lekkich modeli, do których masz darmowy dostęp; prawdopodobnie `gemini-2.5-flash`).
3. Zaprojektuj mały test (np. czy model rekomenduje właściwy lek na daną dolegliwość; czy znajduje poprawne składniki; czy skutki uboczne są zgłaszane prawidłowo).

## Format:

Wyślij plik zip (z zebranymi danymi i zmodyfikowanym plikiem .ipynb)

## Uwagi:

Będziesz zobowiązany do wygenerowania i użycia GOOGLE_API_KEY (jeśli jeszcze go nie posiadasz). Zastanów się, czy możesz inaczej ustrukturyzować zbiór danych w celu lepszego wyszukiwania?
