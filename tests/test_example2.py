# =============================================================================
# test_example2.py — Testy dla Przykladu 2 (serwerownia)
# =============================================================================
#
# Testujemy scenariusz z dokumentacji:
#
# Dziedzina:
#   activate_alarm duration 1
#   activate_alarm causes alarm_on after 1 if smoke
#   smoke causes activate_alarm
#   impossible activate_alarm if maintenance
#   activate_alarm triggers start_ventilation after 1
#   start_ventilation duration 2
#   start_ventilation releases ventilation_on during [0,2]
#   start_ventilation causes ventilation_on after 2 if alarm_on
#
# Scenariusz:
#   OBS = {(smoke & ~maintenance & ~alarm_on & ~ventilation_on, 0)}
#   ACS = {} (pusty!)
#
# Oczekiwane wyniki:
#   - Solver powinien zwrocic DOKLADNIE 1 model
#   - Akcje w E:
#     * (activate_alarm, 0, 1) — z wyzwalacza stanowego smoke causes activate_alarm
#     * (start_ventilation, 2, 4) — z triggera activate_alarm triggers start_ventilation after 1
#
# TESTY DO ZAIMPLEMENTOWANIA:
#
# 1. test_scenario_is_feasible
#    - possibly Sc -> True
#
# 2. test_performing_activate_alarm_at_0
#    - necessary performing activate_alarm at 0 when Sc -> True
#
# 3. test_alarm_on_at_1
#    - necessary alarm_on at 1 when Sc -> True
#
# 4. test_performing_start_ventilation_at_2
#    - necessary performing start_ventilation at 2 when Sc -> True
#
# 5. test_ventilation_on_at_4
#    - necessary ventilation_on at 4 when Sc -> True
#
# 6. test_single_model
#    - solver zwraca dokladnie 1 model
#
# 7. test_state_trigger_fires
#    - Sprawdz ze activate_alarm zostalo dodane do E mimo pustego ACS
#    - (smoke w t=0 powinien wyzwolic akcje)
#
# 8. test_dynamic_trigger_fires
#    - Sprawdz ze start_ventilation zostalo dodane do E
#    - (po zakonczeniu activate_alarm w t=1, trigger after 1 -> start w t=2)
#
# =============================================================================
