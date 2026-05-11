# =============================================================================
# test_example1.py — Testy dla Przykladu 1 (projektor)
# =============================================================================
#
# Testujemy scenariusz z dokumentacji:
#
# Dziedzina:
#   press_power duration 1
#   press_power releases projector_on during [0,1]
#   impossible press_power if projector_on
#
# Scenariusz:
#   OBS = {(~projector_on, 0)}
#   ACS = {(press_power, 0)}
#
# Oczekiwane wyniki:
#   - Solver powinien zwrocic DOKLADNIE 2 modele:
#     * S1: projector_on = False po zakonczeniu akcji (projektor sie nie wlaczyl)
#     * S2: projector_on = True po zakonczeniu akcji (projektor sie wlaczyl)
#
# TESTY DO ZAIMPLEMENTOWANIA:
#
# 1. test_scenario_is_feasible
#    - possibly Sc -> True
#
# 2. test_performing_press_power_at_1
#    - necessary performing press_power at 1 when Sc -> True
#    - (w obu modelach akcja trwa w [0,1], wiec t=1 jest w przedziale)
#
# 3. test_necessary_projector_on_at_2
#    - necessary projector_on at 2 when Sc -> False
#    - (w S1 projektor jest wylaczony)
#
# 4. test_possibly_projector_on_at_2
#    - possibly projector_on at 2 when Sc -> True
#    - (w S2 projektor jest wlaczony)
#
# 5. test_two_models_generated
#    - solver zwraca dokladnie 2 modele
#
# 6. test_inertia_after_occlusion
#    - W modelu S2: projector_on = True w t=2 i t=3 (inercja)
#    - W modelu S1: projector_on = False w t=2 i t=3 (inercja)
#
# =============================================================================
