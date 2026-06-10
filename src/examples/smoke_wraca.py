"""Przyklad 4 — Smoke wraca (test edge-triggered).

Wyzwalacz stanowy strzela tylko na zbocze narastajace warunku:
gdy smoke wraca po wygasnieciu, alarm odpala sie PONOWNIE.
"""

from src.models import (
    Domain, Scenario, Observation,
    CausesStatement, DurationStatement, StateTriggerStatement,
    AtomicFormula, Negation, Conjunction,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.examples.helpers import (
    query_times, solve_and_print, print_validation, print_queries,
    print_domain, print_scenario,
)


def run():
    print("\n" + "=" * 60)
    print("  PRZYKLAD 4: Smoke wraca (edge-triggered)")
    print("=" * 60)
    print("""
Co pokazuje:
  Korzysci z edge-triggered semantyki wyzwalaczy stanowych.
  Scenariusz: smoke pojawia sie w t=0 (alarm strzela), gasnie w t=2
  (alarm milczy), wraca w t=4 (alarm strzela PONOWNIE).

  Demonstruje ze wyzwalacz 'smoke causes activate_alarm':
    - strzela na pierwsze pojawienie sie smoke (t=0),
    - NIE strzela cyklicznie gdy smoke trwa (t=1),
    - milczy gdy smoke=False (t=2, 3),
    - poprawnie reaguje na NOWE zbocze narastajace (t=4).
""")

    # Dziedzina (uproszczona — bez dynamic triggera, zeby skupic sie
    # na edge-triggeringu):
    #   activate_alarm duration 1
    #   activate_alarm causes alarm_on after 1 if smoke
    #   smoke causes activate_alarm     (wyzwalacz stanowy)
    domain = Domain(
        durations=[DurationStatement("activate_alarm", 1)],
        causes=[
            CausesStatement("activate_alarm", AtomicFormula("alarm_on"), 1,
                            AtomicFormula("smoke")),
        ],
        state_triggers=[
            StateTriggerStatement(AtomicFormula("smoke"), "activate_alarm"),
        ],
    )

    # Scenariusz:
    #   OBS: (smoke & ~alarm_on, 0), (~smoke, 2), (smoke, 4)
    #   ACS: (puste)
    scenario = Scenario(
        observations=[
            Observation(
                Conjunction(
                    AtomicFormula("smoke"),
                    Negation(AtomicFormula("alarm_on")),
                ),
                0,
            ),
            Observation(Negation(AtomicFormula("smoke")), 2),
            Observation(AtomicFormula("smoke"), 4),
        ],
        action_declarations=[],
    )

    queries = [
        ("possibly Sc",
         QueryPossiblyScenario()),
        ("necessary performing activate_alarm at 0 when Sc",
         QueryPerforming("necessary", "activate_alarm", 0)),
        ("possibly performing activate_alarm at 2 when Sc",
         QueryPerforming("possibly", "activate_alarm", 2)),
        ("necessary performing activate_alarm at 4 when Sc",
         QueryPerforming("necessary", "activate_alarm", 4)),
        ("necessary alarm_on at 1 when Sc",
         QueryCondition("necessary", AtomicFormula("alarm_on"), 1)),
        ("necessary alarm_on at 5 when Sc",
         QueryCondition("necessary", AtomicFormula("alarm_on"), 5)),
    ]

    print_domain(domain)
    print_scenario(scenario)

    if not print_validation(domain, scenario):
        return

    models = solve_and_print(domain, scenario, extra_times=query_times(queries))
    print_queries(queries, models)
