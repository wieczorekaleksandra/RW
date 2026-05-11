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

## Struktura projektu

```
src/
├── models.py          # Struktury danych (Formula, Domain, Scenario, Model, ...)
├── parser.py          # Parser języka opisu akcji, scenariuszy i kwerend
├── formula_eval.py    # Ewaluacja formuł logicznych H*(formula, t)
├── solver.py          # Silnik generowania modeli
├── query_engine.py    # Silnik odpowiadania na kwerendy
└── main.py            # Punkt wejścia aplikacji
tests/
├── test_parser.py     # Testy parsera
├── test_solver.py     # Testy silnika modeli
├── test_example1.py   # Testy — Przykład 1 (projektor)
└── test_example2.py   # Testy — Przykład 2 (serwerownia)
```

## Uruchomienie

```bash
# Tryb interaktywny
python3 -m src.main

# Wbudowane przykłady
python3 -m src.main --example1    # Projektor
python3 -m src.main --example2    # Serwerownia
python3 -m src.main --examples    # Oba przykłady
```

## Język opisu akcji

Każda instrukcja w osobnej linii:

```
# Czas trwania akcji
press_power duration 1

# Skutek akcji (efekt po delta krokach, opcjonalny warunek)
activate_alarm causes alarm_on after 1 if smoke

# Zawieszenie inercji (okluzja fluentu w przedziale)
press_power releases projector_on during [0,1]

# Skutek dynamiczny (po zakończeniu a, po delta krokach startuje a')
activate_alarm triggers start_ventilation after 1

# Wyzwalacz stanowy (stan systemu automatycznie wywołuje akcję)
smoke causes activate_alarm

# Niewykonalność akcji
impossible press_power if projector_on
impossible press_power at 5
```

## Format scenariusza

```
OBS:
(~projector_on, 0)
(smoke & ~maintenance, 0)
ACS:
(press_power, 0)
```

`OBS` — obserwacje (formuła, chwila czasowa).
`ACS` — deklaracje akcji (nazwa akcji, chwila startu). Może być puste.

## Składnia formuł logicznych

| Operator | Znaczenie |
|----------|-----------|
| `~`      | negacja |
| `&`      | koniunkcja (AND) |
| `\|`     | alternatywa (OR) |
| `->`     | implikacja |
| `<->`    | równoważność |
| `()`     | grupowanie |

Priorytet (od najwyższego): `~` > `&` > `|` > `->` > `<->`

## Kwerendy

```
# Czy scenariusz jest realizowalny?
possibly Sc

# Czy akcja jest wykonywana w chwili t? (w każdym / w jakimś modelu)
necessary performing press_power at 1 when Sc
possibly performing activate_alarm at 0 when Sc

# Czy warunek zachodzi w chwili t? (w każdym / w jakimś modelu)
necessary alarm_on at 1 when Sc
possibly projector_on at 2 when Sc
necessary ~maintenance at 0 when Sc
```

## Przykład sesji interaktywnej

```
Podaj opis dziedziny (pusta linia kończy):
press_power duration 1
press_power releases projector_on during [0,1]
impossible press_power if projector_on

Podaj scenariusz (OBS/ACS, pusta linia kończy):
OBS:
(~projector_on, 0)
ACS:
(press_power, 0)

Generowanie modeli...
  Znaleziono 2 model(i)

Podaj kwerendy (pusta linia kończy):
  > possibly Sc
  => True
  > necessary projector_on at 2 when Sc
  => False
  > possibly projector_on at 2 when Sc
  => True
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
