# TODO — Scenariusze Działań DS1

## Status: Podstawowa wersja działa
Oba przykłady z dokumentacji (projektor + serwerownia) dają poprawne odpowiedzi na kwerendy.

---

## Co działa
- [x] Struktury danych (models.py)
- [x] Parser formuł logicznych (~, &, |, ->, <->)
- [x] Parser dziedziny (causes, duration, releases, triggers, state triggers, impossible)
- [x] Parser scenariuszy (OBS, ACS)
- [x] Parser kwerend (possibly Sc, necessary/possibly performing, necessary/possibly condition)
- [x] Ewaluacja formuł H*(formula, t)
- [x] Solver — generowanie modeli z:
  - [x] Prawem inercji (Z1)
  - [x] Sekwencyjnością akcji (Z2)
  - [x] Efektami akcji z opóźnieniem (causes...after...if)
  - [x] Okluzją / niedeterminizmem (releases)
  - [x] Skutkami dynamicznymi (triggers)
  - [x] Wyzwalaczami stanowymi (α causes a)
  - [x] Niewykonalnością (impossible if / at)
- [x] Silnik kwerend (necessary/possibly)
- [x] Tryb interaktywny + wbudowane przykłady
- [x] README.md

---

## Co trzeba poprawić / dodać

### Krytyczne (wpływa na poprawność)
- [ ] **Cykliczne wyzwalacze stanowe** — jeśli warunek triggera jest ciągle True
      (np. smoke nigdy nie gaśnie), system generuje nieskończony łańcuch akcji.
      Obecnie obcinamy to horyzontem czasowym, ale to hack. Trzeba przemyśleć
      właściwą semantykę (np. trigger strzela tylko raz? strzela ale czeka na wolny slot?)
- [ ] **Warunki początkowe akcji** — Z5 mówi że akcja ma warunek początkowy (if),
      który musi być spełniony żeby akcja mogła się wykonać. Obecnie causes...if
      sprawdza warunek dla efektu, ale nie blokuje samego startu akcji.
- [ ] **Weryfikacja spójności obserwacji** — jeśli OBS zawiera sprzeczne obserwacje
      (np. f=True i f=False w tym samym t), solver powinien zwrócić 0 modeli.
- [ ] **Horyzont czasowy** — obecne obliczanie horyzontu jest przybliżone.
      Powinien uwzględniać kwerendy (max t z kwerend) i kaskadowe triggery.

### Ważne (funkcjonalność)
- [ ] **Testy jednostkowe** — pliki testów istnieją ale są puste (tylko opisy).
      Trzeba napisać faktyczne testy pytest:
  - [ ] tests/test_parser.py (22 testy)
  - [ ] tests/test_solver.py (19 testów)
  - [ ] tests/test_example1.py (6 testów)
  - [ ] tests/test_example2.py (8 testów)
- [ ] **Wczytywanie z pliku** — python3 -m src.main input.txt
      (cała dziedzina + scenariusz + kwerendy w jednym pliku)
- [ ] **Więcej przykładów testowych** — wymyślić scenariusze pokrywające edge case'y:
  - pusty scenariusz (brak OBS, brak ACS)
  - scenariusz z konfliktem czasowym (dwie akcje w tym samym czasie)
  - łańcuch triggerów (A triggers B triggers C)
  - impossible blokujący wyzwalacz stanowy

### Opcjonalne (jakość kodu)
- [ ] **Optymalizacja solvera** — przy dużej okluzji liczba modeli rośnie
      wykładniczo (2^n). Dodać pruning — odcinać gałęzie które już naruszają
      obserwacje lub impossible.
- [ ] **Lepsze komunikaty błędów** — parser powinien mówić co dokładnie
      jest nie tak (numer linii, oczekiwany token).
- [ ] **Ładniejszy wydruk modeli** — tablica z osiami czasu jak w dokumentacji.
- [ ] **Dokumentacja kodu** — docstringi w kluczowych funkcjach.

---

## Jak uruchomić
```bash
python3 -m src.main --examples    # oba przykłady z dokumentacji
python3 -m src.main --example1    # tylko projektor
python3 -m src.main --example2    # tylko serwerownia
python3 -m src.main               # tryb interaktywny
```

## Repo
https://github.com/wieczorekaleksandra/RW
