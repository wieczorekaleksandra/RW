from src.models import (
    Domain, Scenario, Model, ActionExecution,
)
from src.formula_eval import evaluate, get_fluents


def solve(domain: Domain, scenario: Scenario) -> list:
    """
    Glowna funkcja — generuje wszystkie dopuszczalne modele
    dla danej dziedziny i scenariusza.
    Zwraca liste obiektow Model. Pusta lista = scenariusz nierealizowalny.
    """
    time_horizon = _determine_time_horizon(domain, scenario)

    # Zbierz wszystkie fluenty z dziedziny i scenariusza
    all_fluents = _collect_fluents(domain, scenario)

    # Zbuduj poczatkowa relacje wykonan E
    executions = _build_initial_executions(domain, scenario)
    if executions is None:
        return []  # konflikt juz na starcie

    # Generuj modele — przeszukiwanie z rozgalezianiem na okluzjach
    models = _generate_models(domain, scenario, executions, all_fluents, time_horizon)
    return models


def _determine_time_horizon(domain, scenario) -> int:
    """Oblicza horyzont czasowy symulacji."""
    max_t = 0

    for obs in scenario.observations:
        max_t = max(max_t, obs.time)
    for ad in scenario.action_declarations:
        dur = domain.get_duration(ad.action)
        max_t = max(max_t, ad.time + dur)
    for imp in domain.impossible_at:
        max_t = max(max_t, imp.time_point)

    # Dodaj margines na triggery (kaskadowe) — ale nie za duzy
    max_duration = max((d.duration for d in domain.durations), default=1)
    max_trigger_delay = max((t.delay for t in domain.triggers), default=0)
    max_t += max_duration + max_trigger_delay + 2

    return max_t


def _collect_fluents(domain, scenario) -> set:
    """Zbiera nazwy wszystkich fluentow."""
    fluents = set()

    for c in domain.causes:
        fluents |= get_fluents(c.effect)
        if c.condition:
            fluents |= get_fluents(c.condition)
    for r in domain.releases:
        fluents.add(r.fluent)
    for st in domain.state_triggers:
        fluents |= get_fluents(st.condition)
    for imp in domain.impossible_if:
        fluents |= get_fluents(imp.condition)
    for obs in scenario.observations:
        fluents |= get_fluents(obs.formula)

    return fluents


def _build_initial_executions(domain, scenario) -> list:
    """Buduje poczatkowa relacje E z ACS."""
    executions = []
    for ad in scenario.action_declarations:
        dur = domain.get_duration(ad.action)
        executions.append(ActionExecution(ad.action, ad.time, ad.time + dur))
    return executions


def _generate_models(domain, scenario, initial_executions, all_fluents, time_horizon):
    """
    Generuje wszystkie modele iterujac po czasie.
    Dla kazdej chwili t rozgalezia sie na okluzjach.
    """
    # Startujemy z jedna czesciowa struktura
    initial_state = {
        'history': {},
        'occlusion': set(),
        'executions': list(initial_executions),
        'triggers_added': set(),  # sledzenie juz dodanych triggerow
    }

    # Lista stanow do rozwiniecia (kazdy to potencjalny model)
    states = [initial_state]

    for t in range(time_horizon + 1):
        next_states = []
        for state in states:
            expanded = _step(domain, scenario, state, all_fluents, t)
            next_states.extend(expanded)
        states = next_states
        if not states:
            return []

    # Konwertuj stany na obiekty Model
    models = []
    for state in states:
        m = Model(
            history=dict(state['history']),
            occlusion=set(state['occlusion']),
            executions=list(state['executions']),
        )
        models.append(m)

    return models


def _step(domain, scenario, state, all_fluents, t):
    """
    Przetwarza chwile t dla jednego stanu.
    Moze zwrocic wiele stanow (rozgalezienie na okluzji).
    Zwraca liste stanow lub pusta liste jesli ten stan jest nierealizowalny.
    """
    history = state['history']
    executions = state['executions']
    occlusion = state['occlusion']

    # 1. Sprawdz skutki dynamiczne (triggers) dla akcji ktore sie juz zakonczyly
    _apply_dynamic_triggers(domain, state, t)

    # 2. Oblicz okluzje dla chwili t
    occluded_fluents = _get_occluded_fluents(domain, executions, t)
    for f in occluded_fluents:
        occlusion.add((f, t))

    # 3. Zastosuj efekty akcji (causes) dla chwili t
    forced_values = {}
    for c in domain.causes:
        for ex in executions:
            if ex.action == c.action:
                effect_time = ex.start_time + c.delay
                if effect_time == t:
                    if c.condition is None or _safe_eval(c.condition, history, ex.start_time):
                        _apply_effect(c.effect, forced_values)

    # 4. Ustaw wartosci z obserwacji
    obs_values = {}
    for obs in scenario.observations:
        if obs.time == t:
            _apply_effect(obs.formula, obs_values)

    # 5. Dla kazdego fluentu: ustal wartosc lub rozgaleziaj
    branching_fluents = []

    for f in all_fluents:
        if f in obs_values:
            history[(f, t)] = obs_values[f]
        elif f in forced_values and (f, t) not in occlusion:
            history[(f, t)] = forced_values[f]
        elif f in forced_values and (f, t) in occlusion:
            # Efekt wymusza wartosc nawet w okluzji
            history[(f, t)] = forced_values[f]
        elif (f, t) in occlusion:
            branching_fluents.append(f)
        else:
            # Prawo inercji
            if t > 0 and (f, t - 1) in history:
                history[(f, t)] = history[(f, t - 1)]
            elif (f, t) not in history:
                history[(f, t)] = False

    # 6. Rozgaleziaj na okluzjach
    if not branching_fluents:
        states_after_fluents = [state]
    else:
        states_after_fluents = [state]
        for f in branching_fluents:
            new_results = []
            for s in states_after_fluents:
                for val in [True, False]:
                    new_state = _copy_state(s)
                    new_state['history'][(f, t)] = val
                    new_results.append(new_state)
            states_after_fluents = new_results

    # 7. Po ustaleniu wartosci fluentow — sprawdz wyzwalacze stanowe
    #    i waliduj impossible/sekwencyjnosc
    valid_states = []
    for s in states_after_fluents:
        _apply_state_triggers(domain, s, all_fluents, t)
        _apply_dynamic_triggers(domain, s, t)

        if not _check_sequentiality(s['executions']):
            continue
        if not _check_impossible(domain, s['executions'], s['history'], t):
            continue
        valid_states.append(s)

    return valid_states


def _apply_state_triggers(domain, state, all_fluents, t):
    """Sprawdza wyzwalacze stanowe i dodaje akcje do E."""
    history = state['history']
    executions = state['executions']

    # Sprawdz czy w chwili t juz trwa jakas akcja albo jest zaplanowana (sekwencyjnosc)
    # Akcje zajmuja interwaly i nie moga sie nakladac.
    # Jesli trigger dodaje akcje w t, to ta akcja trwa [t, t+dur).
    # Sprawdzamy czy [t, t+dur) naklada sie z jakakolwiek istniejaca.
    # Uproszczenie: nie dodajemy akcji jesli cokolwiek trwa lub startuje w t
    # (start_time <= t < end_time) LUB jest zaplanowane na start w t
    something_active = any(ex.start_time <= t < ex.end_time for ex in executions)
    something_starting = any(ex.start_time == t for ex in executions)
    # Tez nie dodajemy jesli dynamic trigger juz zaplanuje cos na t
    something_ending_and_triggering = any(ex.end_time == t for ex in executions)
    if something_active or something_starting or something_ending_and_triggering:
        return

    for st in domain.state_triggers:
        try:
            if _safe_eval(st.condition, history, t):
                # Sprawdz czy juz nie ma tej akcji w t
                already = any(ex.action == st.action and ex.start_time == t for ex in executions)
                if not already:
                    # Sprawdz impossible
                    blocked = False
                    for imp in domain.impossible_if:
                        if imp.action == st.action and _safe_eval(imp.condition, history, t):
                            blocked = True
                            break
                    for imp in domain.impossible_at:
                        if imp.action == st.action and imp.time_point == t:
                            blocked = True
                            break
                    if not blocked:
                        dur = domain.get_duration(st.action)
                        executions.append(ActionExecution(st.action, t, t + dur))
        except KeyError:
            pass


def _apply_dynamic_triggers(domain, state, t):
    """Sprawdza skutki dynamiczne dla akcji ktore sie juz zakonczyly."""
    executions = state['executions']
    triggers_added = state['triggers_added']

    new_executions = []
    for tr in domain.triggers:
        for ex in executions:
            if ex.action == tr.cause_action and ex.end_time <= t:
                trigger_time = ex.end_time + tr.delay
                key = (tr.triggered_action, trigger_time)
                if key not in triggers_added:
                    dur = 1
                    for d in domain.durations:
                        if d.action == tr.triggered_action:
                            dur = d.duration
                            break
                    already = any(
                        e.action == tr.triggered_action and e.start_time == trigger_time
                        for e in executions
                    )
                    if not already:
                        new_executions.append(ActionExecution(tr.triggered_action, trigger_time, trigger_time + dur))
                    triggers_added.add(key)

    executions.extend(new_executions)


def _check_sequentiality(executions) -> bool:
    """Sprawdza czy interwaly akcji sie nie nakladaja."""
    for i, e1 in enumerate(executions):
        for j, e2 in enumerate(executions):
            if i < j:
                # Interwaly (s1, e1) i (s2, e2) nakladaja sie jesli
                # s1 < e2 AND s2 < e1 (otwarte z prawej)
                if e1.start_time < e2.end_time and e2.start_time < e1.end_time:
                    return False
    return True


def _check_impossible(domain, executions, history, t) -> bool:
    """Sprawdza reguly impossible dla chwili t."""
    for ex in executions:
        if ex.start_time == t:
            # impossible at
            for imp in domain.impossible_at:
                if imp.action == ex.action and imp.time_point == t:
                    return False
            # impossible if
            for imp in domain.impossible_if:
                if imp.action == ex.action:
                    try:
                        if evaluate(imp.condition, history, t):
                            return False
                    except KeyError:
                        pass
    return True


def _get_occluded_fluents(domain, executions, t) -> set:
    """Zwraca fluenty w okluzji w chwili t."""
    occluded = set()
    for rel in domain.releases:
        for ex in executions:
            if ex.action == rel.action:
                occ_start = ex.start_time + rel.interval_start
                occ_end = ex.start_time + rel.interval_end
                if occ_start <= t <= occ_end:
                    occluded.add(rel.fluent)
    return occluded


def _apply_effect(formula, values_dict):
    """Wyciaga wartosci fluentow z prostej formuly (efektu)."""
    from src.models import AtomicFormula, Negation, Conjunction

    if isinstance(formula, AtomicFormula):
        values_dict[formula.name] = True
    elif isinstance(formula, Negation) and isinstance(formula.operand, AtomicFormula):
        values_dict[formula.operand.name] = False
    elif isinstance(formula, Conjunction):
        _apply_effect(formula.left, values_dict)
        _apply_effect(formula.right, values_dict)


def _safe_eval(formula, history, t):
    """Ewaluuje formule, zwraca False jesli brakuje danych."""
    try:
        return evaluate(formula, history, t)
    except KeyError:
        return False


def _copy_state(state):
    """Kopiuje stan (deep copy potrzebnych elementow)."""
    return {
        'history': dict(state['history']),
        'occlusion': set(state['occlusion']),
        'executions': list(state['executions']),
        'triggers_added': set(state['triggers_added']),
    }
