from src.models import (
    Formula, AtomicFormula, Negation, Conjunction,
    Disjunction, Implication, Equivalence,
)


def evaluate(formula: Formula, history: dict, time: int) -> bool:
    """
    Oblicza H*(formula, t).
    history: dict mapujacy (fluent_name, time) -> bool
    Rzuca KeyError jesli fluent nie ma wartosci w danej chwili (np. okluzja bez przypisania).
    """
    if isinstance(formula, AtomicFormula):
        return history[(formula.name, time)]

    if isinstance(formula, Negation):
        return not evaluate(formula.operand, history, time)

    if isinstance(formula, Conjunction):
        return evaluate(formula.left, history, time) and evaluate(formula.right, history, time)

    if isinstance(formula, Disjunction):
        return evaluate(formula.left, history, time) or evaluate(formula.right, history, time)

    if isinstance(formula, Implication):
        return (not evaluate(formula.left, history, time)) or evaluate(formula.right, history, time)

    if isinstance(formula, Equivalence):
        return evaluate(formula.left, history, time) == evaluate(formula.right, history, time)

    raise ValueError(f"Nieznany typ formuly: {type(formula)}")


def get_fluents(formula: Formula) -> set:
    """Zwraca zbior nazw fluentow wystepujacych w formule."""
    if isinstance(formula, AtomicFormula):
        return {formula.name}
    if isinstance(formula, Negation):
        return get_fluents(formula.operand)
    if isinstance(formula, (Conjunction, Disjunction, Implication, Equivalence)):
        return get_fluents(formula.left) | get_fluents(formula.right)
    return set()
