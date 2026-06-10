from src.models import (
    Domain, Scenario, Model, ActionExecution,
)
from src.formula_eval import evaluate, get_fluents
from src.validator import validate


def solve(domain: Domain, scenario: Scenario, extra_times=()) -> list:
    """
    Glowna funkcja — generuje wszystkie dopuszczalne modele
    dla danej dziedziny i scenariusza.
    Zwraca liste obiektow Model. Pusta lista = scenariusz nierealizowalny.

    extra_times: opcjonalne dodatkowe punkty czasowe (np. czasy z kwerend)
    ktore maja byc objete horyzontem.
    """
    # Walidacja scenariusza przed rozwiazywaniem
    errors = validate(domain, scenario)
    if errors:
        return []

    time_horizon = _determine_time_horizon(domain, scenario, extra_times)

    # Zbierz wszystkie fluenty z dziedziny i scenariusza
    all_fluents = _collect_fluents(domain, scenario)

    # Zbuduj poczatkowa relacje wykonan E
    executions = _build_initial_executions(domain, scenario)
    if executions is None:
        return []  # konflikt juz na starcie

    # Generuj modele — przeszukiwanie z rozgalezianiem na okluzjach
    models = _generate_models(domain, scenario, executions, all_fluents, time_horizon)
    return models


def _determine_time_horizon(domain, scenario, extra_times=()) -> int:
    """
    Oblicza horyzont czasowy potrzebny do wygenerowania wszystkich
    istotnych chwil w modelu.

    Domkniety wzgledem:
    1) bazowych punktow czasowych — obserwacje, impossible_at, extra_times
       (czasy z kwerend);
    2) koncow akcji z ACS;
    3) wyzwalaczy stanowych (alfa causes a) — worst case: zakladamy ze
       kazdy moze odpalic w aktualnym max_t i propagujemy jego konsekwencje;
    4) wyzwalaczy dynamicznych (a triggers a' after delta) — iteracyjna
       propagacja az do fixpoint lub limitu iteracji;
    5) opoznien efektow (a causes alpha after delta) — efekt fire'uje w
       start_t + delta, co moze wykraczac poza end_time akcji gdy delta
       > duration.

    Jest to KONSERWATYWNY upper bound — moze rozszerzyc horyzont za daleko
    gdy wyzwalacz stanowy fizycznie sie nie odpali (jego warunek nigdy
    nie zachodzi). Gwarantuje jednak ze wszystkie rzeczywiste zdarzenia
    zostana objete pętlą solvera.

    extra_times: dodatkowe punkty czasowe do uwzglednienia (np. z kwerend).
    """
    # 1. Punkty bazowe
    max_t = 0
    for obs in scenario.observations:
        max_t = max(max_t, obs.time)
    for imp in domain.impossible_at:
        max_t = max(max_t, imp.time_point)
    for t in extra_times:
        max_t = max(max_t, t)

    # 2. Konce akcji z ACS — seed propagacji
    seed = []  # lista (action_name, end_time) do propagacji
    for ad in scenario.action_declarations:
        dur = domain.get_duration(ad.action)
        end_t = ad.time + dur
        seed.append((ad.action, end_t))
        max_t = max(max_t, end_t)

    # 3. Wyzwalacze stanowe — worst case: kazdy moze odpalic w aktualnym
    #    max_t (pozniej niz t=0 jest mozliwe gdy warunek staje sie True
    #    dopiero pod koniec scenariusza wskutek dynamic effect).
    for st in domain.state_triggers:
        dur = domain.get_duration(st.action)
        end_t = max_t + dur
        seed.append((st.action, end_t))
        max_t = end_t

    # 4. Max opoznien causes dla kazdej akcji — efekt 'a causes alpha after
    #    delta' fire'uje w start_t + delta, co moze wykraczac poza
    #    end_time akcji gdy delta > duration.
    causes_max_delay = {}
    for c in domain.causes:
        causes_max_delay[c.action] = max(
            causes_max_delay.get(c.action, 0), c.delay
        )

    # 5. Propagacja iteracyjna przez dynamic triggers + uwzglednienie
    #    opoznien causes. Limit iteracji to bezpiecznik przed teoretycznym
    #    cyklem (w praktyce dynamic triggers DS1 nie tworzą cykli).
    MAX_ITERATIONS = 50
    seen = set()
    pending = list(seed)
    for _ in range(MAX_ITERATIONS):
        new_ends = []
        for (action, end_t) in pending:
            if (action, end_t) in seen:
                continue
            seen.add((action, end_t))

            # Causes effect time = start_t + delay
            d_max = causes_max_delay.get(action, 0)
            dur = domain.get_duration(action)
            start_t = end_t - dur
            max_t = max(max_t, start_t + d_max)

            # Dynamic triggers
            for tr in domain.triggers:
                if tr.cause_action == action:
                    triggered_start = end_t + tr.delay
                    triggered_dur = domain.get_duration(tr.triggered_action)
                    triggered_end = triggered_start + triggered_dur
                    new_ends.append((tr.triggered_action, triggered_end))
                    max_t = max(max_t, triggered_end)
        if not new_ends:
            break
        pending = new_ends

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
        _apply_state_triggers(domain, s, t)
        _apply_dynamic_triggers(domain, s, t)

        if not _check_sequentiality(s['executions']):
            continue
        if not _check_impossible(domain, s['executions'], s['history'], t):
            continue
        if not _check_action_preconditions(domain, s['executions'], s['history'], t):
            continue
        valid_states.append(s)

    return valid_states


def _apply_state_triggers(domain, state, t):
    """Sprawdza wyzwalacze stanowe i dodaje akcje do E.

    Semantyka EDGE-TRIGGERED (zbocze narastajace): wyzwalacz stanowy
    'alfa causes a' strzela tylko wtedy, gdy warunek alfa przechodzi
    z False na True. Dla t=0 traktujemy stan "przed scenariuszem" jako
    brak — jesli warunek jest True na starcie, liczy sie to jako zbocze
    i wyzwalacz strzela.

    Zapobiega to cyklicznym odpaleniom gdy warunek jest stale True
    (np. smoke nigdy nie ganie -> alarm aktywuje sie raz, nie w kolko).
    """
    history = state['history']
    executions = state['executions']

    # Sprawdz czy w chwili t juz trwa jakas akcja albo jest zaplanowana.
    # Akcje zajmuja interwaly i nie moga sie nakladac (Z2 - sekwencyjnosc).
    something_active = any(ex.start_time <= t < ex.end_time for ex in executions)
    something_starting = any(ex.start_time == t for ex in executions)
    something_ending_and_triggering = any(ex.end_time == t for ex in executions)
    if something_active or something_starting or something_ending_and_triggering:
        return

    for st in domain.state_triggers:
        try:
            cond_now = _safe_eval(st.condition, history, t)
            if not cond_now:
                continue
            # Edge-triggered: pomin gdy warunek juz zachodzil w t-1
            # (brak zbocza narastajacego). Dla t=0 nie ma poprzedniej chwili,
            # wiec zawsze strzelamy gdy warunek zachodzi.
            if t > 0 and _safe_eval(st.condition, history, t - 1):
                continue
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


def _check_action_preconditions(domain, executions, history, t) -> bool:
    """
    Z5: Sprawdza warunki poczatkowe akcji startujacych w chwili t.

    Kazda regula 'a causes alpha after delta if pi' implikuje, ze pi
    jest warunkiem poczatkowym (precondition) akcji a — akcja moze sie
    rozpoczac tylko gdy pi zachodzi w jej start_time. Stosujemy semantyke
    KONIUNKCJI: dla akcji a z kilkoma regulami causes, WSZYSTKIE pi musza
    byc spelnione (reguly bez warunku nie naladaja nic).

    Brak danych historycznych dla fluentu w pi traktujemy jako "warunek
    nie spelniony" — wymagamy zeby precondition byl udowodniony True.

    Zwraca False jesli jakakolwiek precondition nie zachodzi -> model
    niepoprawny.
    """
    for ex in executions:
        if ex.start_time == t:
            for c in domain.causes:
                if c.action == ex.action and c.condition is not None:
                    try:
                        if not evaluate(c.condition, history, t):
                            return False
                    except KeyError:
                        return False
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
