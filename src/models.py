from dataclasses import dataclass, field
from typing import Optional


# ========================= FORMULY =========================

class Formula:
    """Klasa bazowa dla formul logicznych."""
    pass


@dataclass
class AtomicFormula(Formula):
    name: str

    def __repr__(self):
        return self.name


@dataclass
class Negation(Formula):
    operand: Formula

    def __repr__(self):
        return f"~{self.operand}"


@dataclass
class Conjunction(Formula):
    left: Formula
    right: Formula

    def __repr__(self):
        return f"({self.left} & {self.right})"


@dataclass
class Disjunction(Formula):
    left: Formula
    right: Formula

    def __repr__(self):
        return f"({self.left} | {self.right})"


@dataclass
class Implication(Formula):
    left: Formula
    right: Formula

    def __repr__(self):
        return f"({self.left} -> {self.right})"


@dataclass
class Equivalence(Formula):
    left: Formula
    right: Formula

    def __repr__(self):
        return f"({self.left} <-> {self.right})"


# ========================= INSTRUKCJE DZIEDZINY =========================

@dataclass
class CausesStatement:
    """a causes α after δ if π"""
    action: str
    effect: Formula
    delay: int
    condition: Optional[Formula] = None


@dataclass
class DurationStatement:
    """a duration d"""
    action: str
    duration: int


@dataclass
class ReleasesStatement:
    """a releases f during [ta, tb]"""
    action: str
    fluent: str
    interval_start: int
    interval_end: int


@dataclass
class TriggersStatement:
    """a triggers a' after δ"""
    cause_action: str
    triggered_action: str
    delay: int


@dataclass
class StateTriggerStatement:
    """α causes a"""
    condition: Formula
    action: str


@dataclass
class ImpossibleIfStatement:
    """impossible a if α"""
    action: str
    condition: Formula


@dataclass
class ImpossibleAtStatement:
    """impossible a at t"""
    action: str
    time_point: int


# ========================= DZIEDZINA =========================

@dataclass
class Domain:
    causes: list = field(default_factory=list)
    durations: list = field(default_factory=list)
    releases: list = field(default_factory=list)
    triggers: list = field(default_factory=list)
    state_triggers: list = field(default_factory=list)
    impossible_if: list = field(default_factory=list)
    impossible_at: list = field(default_factory=list)

    def get_duration(self, action_name: str) -> int:
        for d in self.durations:
            if d.action == action_name:
                return d.duration
        return 1  # domyslnie 1


# ========================= SCENARIUSZ =========================

@dataclass
class Observation:
    formula: Formula
    time: int


@dataclass
class ActionDeclaration:
    action: str
    time: int


@dataclass
class Scenario:
    observations: list = field(default_factory=list)
    action_declarations: list = field(default_factory=list)


# ========================= MODEL =========================

@dataclass
class ActionExecution:
    action: str
    start_time: int
    end_time: int

    def active_at(self, t: int) -> bool:
        # Polotwarty przedzial [start_time, end_time):
        # akcja o duration d startujaca w t0 trwa w chwilach t0..t0+d-1,
        # konczy sie w t0+d (efekty/triggery odpalaja sie w tej chwili).
        return self.start_time <= t < self.end_time


@dataclass
class Model:
    history: dict = field(default_factory=dict)       # (fluent, time) -> bool
    occlusion: set = field(default_factory=set)        # set of (fluent, time)
    executions: list = field(default_factory=list)     # list of ActionExecution


# ========================= KWERENDY =========================

@dataclass
class QueryPossiblyScenario:
    """possibly Sc"""
    pass


@dataclass
class QueryPerforming:
    """necessary/possibly performing a at t when Sc"""
    mode: str  # "necessary" lub "possibly"
    action: str
    time: int


@dataclass
class QueryCondition:
    """necessary/possibly γ at t when Sc"""
    mode: str  # "necessary" lub "possibly"
    formula: Formula
    time: int
