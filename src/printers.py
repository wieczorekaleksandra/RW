"""Funkcje formatowania i wydruku — wspolne dla CLI i GUI."""

from src.models import (
    QueryPerforming, QueryCondition,
    AtomicFormula, Negation, Conjunction, Disjunction,
    Implication, Equivalence,
)
from src.solver import solve
from src.query_engine import execute_query
from src.validator import validate


# Precedencje operatorow logicznych (wieksza = wyzsza). Sluzy do
# formatowania formul z minimalna iloscia nawiasow.
_PREC_EQUIV = 1
_PREC_IMPL = 2
_PREC_OR = 3
_PREC_AND = 4
_PREC_NOT = 5


def format_formula(formula, parent_prec=0):
    """Formatuje formule logiczna z minimalna iloscia nawiasow.

    Czysciejszy niz domyslny __repr__ z models.py, ktory dodaje nawiasy
    wokol kazdej operacji binarnej (np. '(((a & b) & c) & d)' zamiast
    'a & b & c & d').
    """
    if isinstance(formula, AtomicFormula):
        return formula.name
    if isinstance(formula, Negation):
        return "~" + format_formula(formula.operand, _PREC_NOT)
    if isinstance(formula, Conjunction):
        s = f"{format_formula(formula.left, _PREC_AND)} & {format_formula(formula.right, _PREC_AND)}"
        return f"({s})" if parent_prec > _PREC_AND else s
    if isinstance(formula, Disjunction):
        s = f"{format_formula(formula.left, _PREC_OR)} | {format_formula(formula.right, _PREC_OR)}"
        return f"({s})" if parent_prec > _PREC_OR else s
    if isinstance(formula, Implication):
        # -> jest prawostronnie asocjacyjne
        s = f"{format_formula(formula.left, _PREC_IMPL + 1)} -> {format_formula(formula.right, _PREC_IMPL)}"
        return f"({s})" if parent_prec > _PREC_IMPL else s
    if isinstance(formula, Equivalence):
        s = f"{format_formula(formula.left, _PREC_EQUIV + 1)} <-> {format_formula(formula.right, _PREC_EQUIV)}"
        return f"({s})" if parent_prec > _PREC_EQUIV else s
    return repr(formula)


def query_times(queries):
    """Wyciaga czasy wystepujace w kwerendach (do horyzontu solvera)."""
    times = []
    for _, q in queries:
        if isinstance(q, (QueryPerforming, QueryCondition)):
            times.append(q.time)
    return times


def solve_and_print(domain, scenario, extra_times=()):
    """Generuje modele i wypisuje wyniki. Zwraca liste modeli."""
    print("\nGenerowanie modeli...")
    models = solve(domain, scenario, extra_times=extra_times)
    print(f"  Znaleziono {len(models)} model(i)")

    for i, m in enumerate(models):
        print(f"\n  Model {i + 1}:")
        print(format_model_table(m))

    return models


def format_model_table(model):
    """Formatuje model jako tabele: fluenty w wierszach, czas w kolumnach.

    Naglowek pokazuje akcje jako 'name [start..end]'. Komorki pokazuja
    wartosc fluentu (T/F/?) z opcjonalna '*' oznaczajaca okluzje.
    """
    parts = []

    if model.executions:
        actions_str = "    ".join(
            f"{ex.action} [{ex.start_time}..{ex.end_time}]"
            for ex in model.executions
        )
        parts.append(f"    Akcje: {actions_str}")
    else:
        parts.append("    Akcje: (brak)")

    if not model.history:
        return "\n".join(parts)

    max_t = max(t for (_, t) in model.history.keys())
    fluents = sorted(set(f for (f, _) in model.history.keys()))
    fluent_w = max(len(f) for f in fluents + ["t"])

    sep = "+" + "-" * (fluent_w + 2) + "+" + ("----+") * (max_t + 1)

    def row(label, cells):
        body = "|".join(f" {c} " for c in cells)
        return f"| {label.ljust(fluent_w)} |{body}|"

    parts.append("    " + sep)
    parts.append("    " + row("t", [f"{t:>2}" for t in range(max_t + 1)]))
    parts.append("    " + sep)

    has_occlusion = False
    for f in fluents:
        cells = []
        for t in range(max_t + 1):
            val = model.history.get((f, t))
            occ = (f, t) in model.occlusion
            if occ:
                has_occlusion = True
            base = "T" if val is True else ("F" if val is False else "?")
            cells.append(base + ("*" if occ else " "))
        parts.append("    " + row(f, cells))

    parts.append("    " + sep)

    if has_occlusion:
        parts.append("    (* = okluzja)")

    return "\n".join(parts)


def print_validation(domain, scenario):
    """Wyswietla wyniki walidacji. Zwraca True jesli OK."""
    errors = validate(domain, scenario)
    if errors:
        print(f"\nBledy walidacji scenariusza ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        return False
    print("\nWalidacja: OK")
    return True


def print_domain(domain):
    """Wypisuje dziedzine w czytelnej skladni DS1 (jedna instrukcja na linie)."""
    print("\nDziedzina:")
    has_any = False

    for d in domain.durations:
        print(f"  {d.action} duration {d.duration}")
        has_any = True

    for c in domain.causes:
        cond = f" if {format_formula(c.condition)}" if c.condition is not None else ""
        print(f"  {c.action} causes {format_formula(c.effect)} after {c.delay}{cond}")
        has_any = True

    for r in domain.releases:
        print(f"  {r.action} releases {r.fluent} during [{r.interval_start},{r.interval_end}]")
        has_any = True

    for tr in domain.triggers:
        print(f"  {tr.cause_action} triggers {tr.triggered_action} after {tr.delay}")
        has_any = True

    for st in domain.state_triggers:
        print(f"  {format_formula(st.condition)} causes {st.action}")
        has_any = True

    for imp in domain.impossible_if:
        print(f"  impossible {imp.action} if {format_formula(imp.condition)}")
        has_any = True

    for imp in domain.impossible_at:
        print(f"  impossible {imp.action} at {imp.time_point}")
        has_any = True

    if not has_any:
        print("  (pusta)")


def print_scenario(scenario):
    """Wypisuje scenariusz (OBS + ACS) w czytelnej skladni."""
    print("\nScenariusz:")

    if scenario.observations:
        print("  OBS:")
        for obs in scenario.observations:
            print(f"    ({format_formula(obs.formula)}, {obs.time})")
    else:
        print("  OBS: (puste)")

    if scenario.action_declarations:
        print("  ACS:")
        for ad in scenario.action_declarations:
            print(f"    ({ad.action}, {ad.time})")
    else:
        print("  ACS: (puste)")


def print_queries(queries, models):
    """Uruchamia liste (etykieta, obiekt_kwerendy) i wypisuje wyniki."""
    print("\nKwerendy:")
    for label, query in queries:
        result = execute_query(query, models)
        print(f"  {label} => {result}")
