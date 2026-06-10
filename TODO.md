# TODO — Scenariusze Działań DS1

## Status: Wersja beta
Solver, walidator i silnik kwerend działają. Wszystkie 5 przykładów
(projektor, serwerownia, błędny scenariusz, smoke wraca, Z5 precondition)
dają poprawne odpowiedzi.
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
  - [x] **Edge-triggered semantyka wyzwalaczy stanowych** — trigger
        `α causes a` strzela tylko gdy α przechodzi z False na True
        (zbocze narastające). Eliminuje cykliczne odpalanie gdy warunek
        trwa. Dla `t=0` „stan przed scenariuszem" traktujemy jako False
        — warunek True na starcie liczy się jako zbocze.
        (Zobacz przykład 4 — smoke wraca i alarm strzela ponownie.)
  - [x] **Z5 — warunek początkowy akcji** — reguła `a causes α after δ
        if π` implikuje że π jest preconditionem akcji `a`. Semantyka
        koniunkcji: wszystkie π z reguł `causes` dla akcji muszą być
        spełnione w start_time. Brak danych → odrzucamy.
        (Zobacz przykład 5 — reboot wymaga ~broken, scenariusz z broken
        daje 0 modeli.)
- [x] **Półotwarta semantyka czasu** — akcja `[start, start+duration)`,
      efekt/triggerowana akcja w chwili `start+duration`
- [x] **Horyzont domknięty (W1)** — domknięty względem:
  - obserwacji, `impossible_at`, czasów z kwerend (`extra_times`);
  - końców akcji z ACS;
  - **wyzwalaczy stanowych** — worst case: odpalą w aktualnym `max_t`,
    cascada wliczona;
  - **opóźnień `causes ... after δ`** — efekt może wykraczać poza
    koniec akcji o `δ - duration`;
  - dynamic triggers — iteracyjna propagacja do fixpoint.
  Konserwatywny upper bound (może przeszacować gdy state trigger się
  fizycznie nie odpali). Patrz [W2 jako zapas](#horyzont-w2--zapas).
- [x] Silnik kwerend (`possibly Sc`, `necessary/possibly performing`,
      `necessary/possibly γ`)
- [x] Wbudowane przykłady — projektor, serwerownia, błędny scenariusz,
      smoke wraca (edge-triggered demo), Z5 precondition demo
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

- [ ] **Docstringi** w kluczowych funkcjach `solver.py` — szczególnie `_step`
      (najważniejsza funkcja, ma komentarze ale brak formalnego docstringa
      opisującego 7 kroków).

---

## Jak uruchomić

```bash
python3 -m src.main --example1    # Projektor — niedeterminizm z releases
python3 -m src.main --example2    # Serwerownia — state trigger + dynamic trigger
python3 -m src.main --example3    # Bledny scenariusz — walidator
python3 -m src.main --example4    # Smoke wraca — edge-triggered state trigger
python3 -m src.main --example5    # Z5 — precondition blokuje start akcji
python3 -m src.main --examples    # Wszystko po kolei
```

## Repo
https://github.com/wieczorekaleksandra/RW

---

## Horyzont: W2 — zapas

Obecny horyzont (W1, [solver.py:`_determine_time_horizon`](src/solver.py))
to **konserwatywny upper bound**. Może przeszacować horyzont w sytuacjach
gdy wyzwalacz stanowy fizycznie się nie odpala (np. jego warunek nigdy
nie zachodzi w danym scenariuszu).

Przykład: w `--example2` (serwerownia) horyzont = 8 mimo że wszystkie
„interesujące" zdarzenia kończą się w t=4. Powód: konserwatywne
założenie „state trigger może odpalić w `max_t`" → cascada
`activate_alarm(end=5) → start_ventilation(end=8)`. W praktyce trigger
odpala w t=0 i cascada kończy się w t=4. Wartości w t=5..8 to tylko
inercja, ale powiększają wydruk.

**Gdyby p. profesor nie zaakceptowała W1** (np. uznała przeszacowanie
za niepoprawne semantycznie), istnieje wariant W2:

### W2 — Dynamiczne rozszerzanie horyzontu w pętli solvera

**Idea:** zamiast precomputować horyzont upfront, niech rośnie razem
ze stanem podczas iteracji solvera.

**Zmiana w `_generate_models` ([solver.py](src/solver.py)):**

```python
def _generate_models(domain, scenario, initial_executions,
                     all_fluents, base_horizon):
    states = [initial_state]
    t = 0
    horizon = base_horizon  # tylko obs, impossible_at, ACS, queries
    MAX_HORIZON_CAP = 1000  # bezpiecznik przed cyklem

    while t <= horizon:
        next_states = []
        for state in states:
            expanded = _step(domain, scenario, state, all_fluents, t)
            next_states.extend(expanded)
            # Po _step nowe akcje moga byc w state['executions'].
            # Rozszerz horizon na podstawie ich end_time + max delay
            # causes + jeden krok dynamic trigger.
            for s in expanded:
                horizon = max(horizon, _required_horizon(s, domain))
        states = next_states
        t += 1
        if horizon > MAX_HORIZON_CAP:
            raise SolverError(
                "horyzont przekroczyl cap — prawdopodobny cykl"
            )
    return [...]
```

`_required_horizon(state, domain)` zwraca:
- `max(ex.end_time for ex in state['executions'])`
- `+ max delay causes` dla akcji w state
- `+ jeden krok dynamic trigger` (delay + duration triggered_action).

**Zalety W2:**
- Dokładny — horyzont rośnie tylko gdy faktycznie pojawi się nowa akcja
  w stanie. Brak przeszacowania dla state triggerów które się nie odpalają.
- Bardziej zbliżony do intuicji „symuluj aż przestanie się dziać cokolwiek".

**Wady W2:**
- Bardziej skomplikowane — pętla solver musi pilnować zbieżności.
- Wymaga cap bezpieczeństwa (`MAX_HORIZON_CAP`) i decyzji co zrobić przy
  jego przekroczeniu (rzucić błąd? obciąć?).
- Większa szansa na bugi przy edge case'ach (cykliczne triggery,
  rozgałęzienia na okluzjach — każde rozgałęzienie ma własny horyzont).
- Trudniejsze do udowodnienia formalnie (bo horyzont jest funkcją stanu).

**Status:** W1 jest aktualną implementacją. W2 do wdrożenia tylko gdy
W1 zostanie odrzucone.
