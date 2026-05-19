from src.models import Domain, Scenario


class ValidationError:
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __repr__(self):
        return f"[{self.code}] {self.message}"


def validate(domain: Domain, scenario: Scenario) -> list:
    """
    Sprawdza poprawność scenariusza względem dziedziny i założeń DS1.
    Zwraca listę ValidationError. Pusta lista = wszystko OK.
    """
    errors = []
    errors.extend(_check_contradictory_observations(scenario))
    errors.extend(_check_acs_sequentiality(domain, scenario))
    errors.extend(_check_impossible_at(domain, scenario))
    errors.extend(_check_durations(domain))
    errors.extend(_check_causes_delays(domain))
    errors.extend(_check_undefined_actions_in_acs(domain, scenario))
    return errors


# ========================= SPRAWDZENIA =========================

def _check_contradictory_observations(scenario) -> list:
    """
    Sprawdza czy obserwacje nie są sprzeczne — ten sam fluent
    nie może mieć wartości True i False w tej samej chwili.
    """
    errors = []
    # Zbierz (fluent, time) -> wymuszona wartość
    assigned = {}  # (fluent, time) -> (value, observation_index)

    for i, obs in enumerate(scenario.observations):
        values = {}
        _extract_values(obs.formula, values)
        for fluent, value in values.items():
            key = (fluent, obs.time)
            if key in assigned:
                prev_value, prev_idx = assigned[key]
                if prev_value != value:
                    errors.append(ValidationError(
                        "OBS_CONTRADICTION",
                        f"Sprzeczne obserwacje: fluent '{fluent}' w t={obs.time} "
                        f"ma wartość {prev_value} (OBS #{prev_idx + 1}) "
                        f"i {value} (OBS #{i + 1})"
                    ))
            else:
                assigned[key] = (value, i)

    return errors


def _check_acs_sequentiality(domain, scenario) -> list:
    """
    Z2: Sprawdza czy akcje zadeklarowane w ACS nie nakładają się czasowo.
    """
    errors = []
    declarations = []
    for ad in scenario.action_declarations:
        dur = domain.get_duration(ad.action)
        declarations.append((ad.action, ad.time, ad.time + dur))

    for i, (a1, s1, e1) in enumerate(declarations):
        for j, (a2, s2, e2) in enumerate(declarations):
            if i < j and s1 < e2 and s2 < e1:
                errors.append(ValidationError(
                    "ACS_OVERLAP",
                    f"Z2 — nakładające się akcje: "
                    f"'{a1}' [{s1},{e1}) i '{a2}' [{s2},{e2})"
                ))

    return errors


def _check_impossible_at(domain, scenario) -> list:
    """
    Z8: Sprawdza czy ACS nie deklaruje akcji w punktach czasowych
    oznaczonych jako impossible.
    """
    errors = []
    for ad in scenario.action_declarations:
        for imp in domain.impossible_at:
            if imp.action == ad.action and imp.time_point == ad.time:
                errors.append(ValidationError(
                    "IMPOSSIBLE_AT",
                    f"Z8 — akcja '{ad.action}' zadeklarowana w t={ad.time}, "
                    f"ale jest tam impossible"
                ))
    return errors


def _check_durations(domain) -> list:
    """
    Z5: Czas trwania akcji musi być d >= 1.
    """
    errors = []
    for d in domain.durations:
        if d.duration < 1:
            errors.append(ValidationError(
                "DURATION_INVALID",
                f"Z5 — akcja '{d.action}' ma duration={d.duration}, "
                f"wymagane d >= 1"
            ))
    return errors


def _check_causes_delays(domain) -> list:
    """
    Z5: Efekty akcji muszą wystąpić po czasie d >= 1.
    """
    errors = []
    for c in domain.causes:
        if c.delay < 1:
            errors.append(ValidationError(
                "DELAY_INVALID",
                f"Z5 — akcja '{c.action}' ma causes z delay={c.delay}, "
                f"wymagane d >= 1"
            ))
    return errors


def _check_undefined_actions_in_acs(domain, scenario) -> list:
    """
    Sprawdza czy akcje w ACS mają zdefiniowany czas trwania w dziedzinie.
    """
    errors = []
    defined_actions = {d.action for d in domain.durations}
    # Dodaj akcje które pojawiają się w causes/triggers/etc.
    all_known = set(defined_actions)
    for c in domain.causes:
        all_known.add(c.action)
    for t in domain.triggers:
        all_known.add(t.cause_action)
        all_known.add(t.triggered_action)
    for st in domain.state_triggers:
        all_known.add(st.action)
    for imp in domain.impossible_if:
        all_known.add(imp.action)
    for imp in domain.impossible_at:
        all_known.add(imp.action)

    for ad in scenario.action_declarations:
        if ad.action not in all_known:
            errors.append(ValidationError(
                "ACTION_UNKNOWN",
                f"Akcja '{ad.action}' w ACS nie występuje nigdzie w dziedzinie"
            ))

    return errors


# ========================= HELPERS =========================

def _extract_values(formula, values):
    """Wyciąga wartości fluentów z formuły obserwacji."""
    from src.models import AtomicFormula, Negation, Conjunction

    if isinstance(formula, AtomicFormula):
        values[formula.name] = True
    elif isinstance(formula, Negation) and isinstance(formula.operand, AtomicFormula):
        values[formula.operand.name] = False
    elif isinstance(formula, Conjunction):
        _extract_values(formula.left, values)
        _extract_values(formula.right, values)
