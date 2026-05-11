from src.models import (
    Model, QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.formula_eval import evaluate


def execute_query(query, models: list) -> bool:
    """Wykonuje kwerendę na liscie modeli."""
    if isinstance(query, QueryPossiblyScenario):
        return query_possibly_scenario(models)

    if isinstance(query, QueryPerforming):
        return query_performing(query.action, query.time, models, query.mode)

    if isinstance(query, QueryCondition):
        return query_condition(query.formula, query.time, models, query.mode)

    raise ValueError(f"Nieznany typ kwerendy: {type(query)}")


def query_possibly_scenario(models) -> bool:
    """possibly Sc — True jesli istnieje >= 1 model."""
    return len(models) > 0


def query_performing(action_name, time, models, mode) -> bool:
    """necessary/possibly performing a at t when Sc."""
    if not models:
        return mode == "necessary"  # vacuous truth

    results = []
    for m in models:
        found = any(ex.active_at(time) for ex in m.executions if ex.action == action_name)
        results.append(found)

    if mode == "necessary":
        return all(results)
    else:  # possibly
        return any(results)


def query_condition(formula, time, models, mode) -> bool:
    """necessary/possibly γ at t when Sc."""
    if not models:
        return mode == "necessary"  # vacuous truth

    results = []
    for m in models:
        try:
            val = evaluate(formula, m.history, time)
            results.append(val)
        except KeyError:
            results.append(False)

    if mode == "necessary":
        return all(results)
    else:  # possibly
        return any(results)
