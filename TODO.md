# TODO — Scenariusze Działań DS1

## Status: Wersja beta
Solver, walidator i silnik kwerend działają. Wszystkie 3 przykłady
(projektor, serwerownia, błędny scenariusz) dają poprawne odpowiedzi.
Parser DSL został usunięty — dziedzinę, scenariusz i kwerendy buduje się
bezpośrednio z obiektów Pythona (`src/models.py`). Docelowy interfejs to GUI.

---

## Co działa

- [x] Struktury danych ([models.py](src/models.py))
- [x] Ewaluacja formuł H\*(formula, t) ([formula_eval.py](src/formula_eval.py))
- [x] **Walidator** ([validator.py](src/validator.py)) — 6 typów sprawdzeń:
  - [x] sprzeczne obserwacje (`OBS_CONTRADICTION`)
  - [x] nakładające się akcje w ACS — Z2 (`ACS_OVERLAP`)
  - [x] zakaz w `impossible_at` dla ACS — Z8 (`IMPOSSIBLE_AT`)
  - [x] duration ≥ 1 — Z5 (`DURATION_INVALID`)
  - [x] delay ≥ 1 dla `causes` — Z5 (`DELAY_INVALID`)
  - [x] akcje nieznane w dziedzinie (`ACTION_UNKNOWN`)
- [x] Solver — generowanie modeli z:
  - [x] Prawem inercji (Z1)
  - [x] Sekwencyjnością akcji (Z2, półotwarte `[start, end)`)
  - [x] Efektami akcji z opóźnieniem (`causes ... after δ if π`)
  - [x] Okluzją / niedeterminizmem (`releases`)
  - [x] Skutkami dynamicznymi (`triggers`)
  - [x] Wyzwalaczami stanowymi (`α causes a`)
  - [x] Niewykonalnością (`impossible if` / `at`)
- [x] **Półotwarta semantyka czasu** — akcja `[start, start+duration)`,
      efekt/triggerowana akcja w chwili `start+duration`
- [x] **Horyzont domknięty względem triggerów dynamicznych** — BFS przez graf
      wyzwoleń + uwzględnienie czasów z kwerend
- [x] Silnik kwerend (`possibly Sc`, `necessary/possibly performing`,
      `necessary/possibly γ`)
- [x] Wbudowane przykłady — projektor, serwerownia, błędny scenariusz
- [x] README.md z API Pythona

---

## Co trzeba zrobić

### Krytyczne (przed pełną wersją)

- [ ] **GUI** — główny następny krok, zastępuje usunięty parser DSL.
      Formularz powinien budować obiekty z `models.py` dokładnie tak jak
      `run_example1/2/3` w [main.py](src/main.py). Reszta kodu nie wymaga zmian.
      Sugerowany stack: tkinter (bez zależności) albo PyQt/PySide.

- [ ] **Testy jednostkowe pytest** — pliki testów istnieją jako szkielety
      opisowe, brak faktycznych asercji:
  - [ ] [tests/test_solver.py](tests/test_solver.py) — 19 testów
        (sekwencyjność, impossible, okluzja, inercja, triggery, edge case'y)
  - [ ] [tests/test_example1.py](tests/test_example1.py) — 6 testów
        dla scenariusza projektor
  - [ ] [tests/test_example2.py](tests/test_example2.py) — 8 testów
        dla scenariusza serwerownia
  - [ ] dodać `tests/test_validator.py` (6 typów błędów)
  - [ ] dodać `tests/test_formula_eval.py` (ewaluacja, get_fluents, KeyError)

- [ ] **Warunki początkowe akcji (Z5)** — założenie mówi że akcja ma warunek
      początkowy który musi być spełniony żeby akcja mogła się **wykonać**.
      Obecnie `causes ... if π` sprawdza `π` tylko dla efektu w
      [solver.py:189](src/solver.py#L189), nie blokuje samego startu akcji.
      Trzeba zdecydować: czy `if` przy `causes` to warunek startu czy tylko
      efektu (może osobna instrukcja `precondition`?).

- [ ] **Cykliczne wyzwalacze stanowe** — `smoke causes activate_alarm` przy
      stale True `smoke` odpala alarm ponownie po zakończeniu pierwszego cyklu
      (widać w przykładzie 2 — drugi `activate_alarm` w t=5).
      Obecny strażnik tylko opóźnia problem. Trzeba zdecydować semantykę:
      strzela raz? edge-triggered (przy zmianie False→True)? level-triggered
      (obecnie tak)? Dokumentacja DS1 tego nie precyzuje.

### Ważne (jakość i UX)

- [ ] **Lepszy wydruk modeli** — obecny wydruk listy stringów
      `['F*', 'T*', 'T', 'T']` jest mało czytelny. Tabela z poziomą osią czasu
      i pionowymi fluentami (jak w `main.tex`) byłaby znacznie lepsza.
      Bonus: linia z aktywnymi akcjami.

- [ ] **Więcej przykładów testowych** — edge case'y do sprawdzenia:
  - pusty scenariusz (brak OBS, brak ACS)
  - łańcuch triggerów `A triggers B triggers C` (test horyzontu BFS)
  - `impossible` blokujący wyzwalacz stanowy
  - kwerendy w odległej przyszłości (t > horyzontu)

- [ ] **Optymalizacja solvera** — przy `n` chwilach okluzji bez efektu
      generujemy `2^n` modeli. Dodać pruning: jeśli wybór True/False w okluzji
      od razu narusza obserwację albo `impossible`, odetnij gałąź zamiast
      rozwijać do końca.

### Dokumentacja

- [ ] **Synchronizacja `main.tex`** — przykład 2 w dokumencie mówi
      „istnieje dokładnie jedna struktura", ale implementacja generuje 4 modele
      (warianty `ventilation_on` w okluzji). Trzeba albo zmienić tekst dokumentu,
      albo uzasadnić że wszystkie są obserwacyjnie równoważne dla podanych
      kwerend.

- [ ] **Docstringi** w kluczowych funkcjach `solver.py` — szczególnie `_step`
      (najważniejsza funkcja, ma komentarze ale brak formalnego docstringa
      opisującego 7 kroków).

---

## Jak uruchomić

```bash
python3 -m src.main --example1    # Projektor — niedeterminizm z releases
python3 -m src.main --example2    # Serwerownia — state trigger + dynamic trigger
python3 -m src.main --example3    # Bledny scenariusz — walidator
python3 -m src.main --examples    # Wszystko po kolei
```

## Repo
https://github.com/wieczorekaleksandra/RW
