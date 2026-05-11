# =============================================================================
# test_parser.py — Testy parsera
# =============================================================================
#
# TESTY DO ZAIMPLEMENTOWANIA:
#
# --- Testy parsowania formul ---
#
# 1. test_parse_atomic — "projector_on" -> AtomicFormula("projector_on")
# 2. test_parse_negation — "~smoke" -> Negation(AtomicFormula("smoke"))
# 3. test_parse_conjunction — "smoke & alarm_on" -> Conjunction(...)
# 4. test_parse_disjunction — "a | b" -> Disjunction(...)
# 5. test_parse_implication — "a -> b" -> Implication(...)
# 6. test_parse_equivalence — "a <-> b" -> Equivalence(...)
# 7. test_parse_complex — "~a & (b | c)" -> poprawne drzewo
# 8. test_parse_precedence — "a | b & c" -> a | (b & c), nie (a | b) & c
#
# --- Testy parsowania instrukcji dziedziny ---
#
# 9. test_parse_duration — "press_power duration 1"
# 10. test_parse_causes — "a causes effect after 1 if cond"
# 11. test_parse_causes_no_condition — "a causes effect after 1"
# 12. test_parse_releases — "a releases f during [0,2]"
# 13. test_parse_triggers — "a triggers b after 1"
# 14. test_parse_state_trigger — "smoke causes activate_alarm"
# 15. test_parse_impossible_if — "impossible a if cond"
# 16. test_parse_impossible_at — "impossible a at 5"
#
# --- Testy parsowania scenariusza ---
#
# 17. test_parse_observations — OBS z jednym i wieloma wpisami
# 18. test_parse_action_declarations — ACS z jednym i wieloma wpisami
# 19. test_parse_empty_acs — pusty ACS
#
# --- Testy parsowania kwerend ---
#
# 20. test_parse_possibly_scenario — "possibly Sc"
# 21. test_parse_necessary_performing — "necessary performing a at 0 when Sc"
# 22. test_parse_possibly_condition — "possibly alarm_on at 1 when Sc"
#
# =============================================================================
