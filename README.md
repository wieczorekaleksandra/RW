# Scenariusze Działań — System DS1

Implementacja języka opisu akcji i języka kwerend dla klasy systemów dynamicznych DS1.

Projekt realizowany w ramach przedmiotu **Reprezentacja Wiedzy** (MSI, semestr letni 2025/2026).

## Autorzy

- Aleksandra Wieczorek (Koordynator)
- Grzegorz Prasek
- Hubert Sobociński
- Jakub Kindracki
- Mykhailo Shamrai
- Stanisław Zaprzalski
- Wiktor Kobielski

## Opis projektu

System pozwala na:
1. Definiowanie dziedziny akcji (skutki, czas trwania, triggery, ograniczenia)
2. Definiowanie scenariuszy (obserwacje + deklaracje akcji)
3. Generowanie wszystkich dopuszczalnych modeli
4. Odpowiadanie na kwerendy:
   - **Czy scenariusz jest realizowalny?**
   - **Czy w chwili t wykonywana jest akcja A?**
   - **Czy w chwili t warunek γ zachodzi zawsze/kiedykolwiek?**

## Wymagania

- Python 3.10+
- Brak zewnętrznych zależności

## Status

Wersja beta — silnik modeli, walidator i kwerendy działają. **Parser języka tekstowego
został usunięty** — dziedzinę, scenariusz i kwerendy buduje się bezpośrednio z obiektów
Pythona (`src/models.py`). Docelowy interfejs to GUI (TODO), który będzie tworzył
te same obiekty z formularza.

## Struktura projektu

```
src/
├── models.py             # Struktury danych (Formula, Domain, Scenario, Model, ...)
├── formula_eval.py       # Ewaluacja formuł logicznych H*(formula, t)
├── validator.py          # Walidacja scenariusza wzgledem zalozen DS1
├── solver.py             # Silnik generowania modeli
├── query_engine.py       # Silnik odpowiadania na kwerendy
├── gui.py                # Okienkowy interfejs tkinter (--gui)
├── main.py               # CLI dispatch — wywoluje przyklady lub GUI
└── examples/             # Wbudowane przyklady
    ├── helpers.py        # Wspolne funkcje (solve_and_print, ...)
    ├── projektor.py      # Przyklad 1 — niedeterminizm z releases
    ├── serwerownia.py    # Przyklad 2 — state trigger + dynamic trigger
    ├── bledny.py         # Przyklad 3 — walidator odrzuca scenariusz
    ├── smoke_wraca.py    # Przyklad 4 — edge-triggered state trigger
    └── precondition_z5.py # Przyklad 5 — Z5 blokuje start akcji
tests/
├── test_solver.py        # Testy silnika modeli (TODO — szkielety)
├── test_example1.py      # Testy — Przyklad 1 (projektor) (TODO — szkielety)
└── test_example2.py      # Testy — Przyklad 2 (serwerownia) (TODO — szkielety)
```

## Uruchomienie

### GUI (zalecane)

```bash
python3 -m src.main --gui
```

Otwiera okno tkinter z 5 zakładkami (Fluenty i akcje, Dziedzina, Scenariusz,
Kwerendy, Wyniki). Wszystkie instrukcje dodajesz przez przyciski + dialogi
z dropdownami — nie ma parsera, nie trzeba wpisywać składni z palca.

**Najszybszy test:** kliknij `#2 Serwerownia` w pasku górnym (wczyta cały
przykład), przejdź na zakładkę `5. Wyniki`, kliknij `ROZWIAZ ▶`.

### CLI — wbudowane przykłady

```bash
python3 -m src.main --example1    # Projektor (niedeterminizm z releases)
python3 -m src.main --example2    # Serwerownia (state trigger + dynamic trigger)
python3 -m src.main --example3    # Bledny scenariusz (walidator)
python3 -m src.main --example4    # Smoke wraca (edge-triggered state trigger)
python3 -m src.main --example5    # Z5 — precondition blokuje start akcji
python3 -m src.main --examples    # Wszystkie powyzsze
```

## Model czasu

**Półotwarta interpretacja czasu trwania akcji.** Jeżeli akcja `a` rozpoczyna się
w chwili `t0` i ma czas trwania `d`, to:

- akcja jest **wykonywana** w chwilach `τ` spełniających `t0 ≤ τ < t0 + d`
- chwila `t0 + d` jest momentem **zakończenia** akcji — pojawiają się w niej efekty
  końcowe (`causes ... after d`) i mogą wystartować akcje wyzwalane dynamicznie
  (`triggers ... after 0`)
- kolejna akcja może rozpocząć się w chwili `t0 + d` bez naruszenia sekwencyjności

Czyli `(a, 0, 2)` znaczy: `a` wykonuje się w `τ = 0, 1`, kończy się w `2`, efekt
w `2`. Następna akcja może startować w `2`.

Reguły szczegółowe:
- `a causes α after δ if π`: efekt `α` zachodzi w `t0 + δ`, warunek `π` sprawdzany
  w `t0`. **Z5:** `π` jest również warunkiem początkowym akcji — akcja `a` nie
  wystartuje w `t0` jeśli `π` nie zachodzi (semantyka koniunkcji dla wielu reguł
  `causes` tej samej akcji).
- `a triggers a' after δ`: akcja `a'` startuje w `end_time + δ` (przy `δ = 0` od razu)
- `α causes a` (wyzwalacz stanowy, **edge-triggered**): akcja `a` startuje w `t`
  tylko gdy `α` przechodzi z False na True (zbocze narastające) i nie trwa żadna
  inna akcja. Dla `t = 0` „stan przed scenariuszem" traktujemy jako False — jeśli
  `α` jest True na starcie, wyzwalacz odpala. Zapobiega to cyklicznym odpalaniom
  gdy warunek trwa stale True.
- `impossible a if α` / `impossible a at t`: blokuje **start** akcji

**Horyzont modelu** ([solver.py:`_determine_time_horizon`](src/solver.py)) to
konserwatywny upper bound domknięty względem: obserwacji, `impossible_at`, czasów
z kwerend, końców akcji z ACS, wyzwalaczy stanowych (worst case — odpalą w
aktualnym `max_t`), opóźnień `causes ... after δ`, oraz iteracyjnej propagacji
dynamic triggers. Patrz [TODO.md — Horyzont W2 jako zapas](TODO.md#horyzont-w2--zapas).

## Język opisu akcji (API Pythona)

Wszystkie konstrukcje języka mają odpowiadające klasy w `src/models.py`.

```python
from src.models import (
    Domain, DurationStatement, CausesStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement,
    ImpossibleIfStatement, ImpossibleAtStatement,
    AtomicFormula, Negation, Conjunction,
)

domain = Domain(
    # Czas trwania: press_power duration 1
    durations=[DurationStatement("press_power", 1)],

    # Skutek po opoznieniu z warunkiem: a causes alarm_on after 1 if smoke
    causes=[CausesStatement(
        action="activate_alarm",
        effect=AtomicFormula("alarm_on"),
        delay=1,
        condition=AtomicFormula("smoke"),
    )],

    # Okluzja fluentu w przedziale: press_power releases projector_on during [0,1]
    releases=[ReleasesStatement("press_power", "projector_on", 0, 1)],

    # Skutek dynamiczny: activate_alarm triggers start_ventilation after 1
    triggers=[TriggersStatement("activate_alarm", "start_ventilation", 1)],

    # Wyzwalacz stanowy: smoke causes activate_alarm
    state_triggers=[StateTriggerStatement(
        condition=AtomicFormula("smoke"),
        action="activate_alarm",
    )],

    # Niewykonalnosc:
    impossible_if=[ImpossibleIfStatement(
        action="press_power",
        condition=AtomicFormula("projector_on"),
    )],
    impossible_at=[ImpossibleAtStatement("reboot", 0)],
)
```

### Klasy formuł

| Klasa                       | Znaczenie                |
| --------------------------- | ------------------------ |
| `AtomicFormula("f")`        | atom (fluent)            |
| `Negation(F)`               | negacja `~F`             |
| `Conjunction(F1, F2)`       | koniunkcja `F1 & F2`     |
| `Disjunction(F1, F2)`       | alternatywa `F1 \| F2`   |
| `Implication(F1, F2)`       | implikacja `F1 -> F2`    |
| `Equivalence(F1, F2)`       | równoważność `F1 <-> F2` |

## Scenariusz

```python
from src.models import Scenario, Observation, ActionDeclaration

scenario = Scenario(
    observations=[
        Observation(Negation(AtomicFormula("projector_on")), time=0),
    ],
    action_declarations=[
        ActionDeclaration("press_power", time=0),
    ],
)
```

## Kwerendy

```python
from src.models import QueryPossiblyScenario, QueryPerforming, QueryCondition
from src.solver import solve
from src.query_engine import execute_query

models = solve(domain, scenario)

# possibly Sc — czy scenariusz jest realizowalny?
execute_query(QueryPossiblyScenario(), models)

# necessary/possibly performing a at t when Sc
execute_query(QueryPerforming("necessary", "press_power", 1), models)
execute_query(QueryPerforming("possibly", "activate_alarm", 0), models)

# necessary/possibly γ at t when Sc
execute_query(QueryCondition("necessary", AtomicFormula("alarm_on"), 1), models)
execute_query(QueryCondition("possibly", AtomicFormula("projector_on"), 2), models)
```

## Założenia klasy DS1

| Nr | Założenie |
|----|-----------|
| Z1 | Prawo inercji — fluenty nie zmieniają się bez powodu |
| Z2 | Sekwencyjność — max jedna akcja w danej chwili |
| Z3 | Pełna informacja o akcjach i ich skutkach |
| Z4 | Czas dyskretny, liniowy (liczby naturalne) |
| Z5 | Akcje mają warunek początkowy, efekty i czas trwania |
| Z6 | Wartości fluentów mogą być nieznane w trakcie akcji (okluzja) |
| Z7 | Skutki środowiskowe i dynamiczne |
| Z8 | Niewykonalność akcji (warunki logiczne lub punkty czasowe) |
| Z9 | Wyzwalacze stanowe — stan systemu może automatycznie wywołać akcję |
