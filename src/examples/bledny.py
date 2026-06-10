"""Przyklad 3 — celowo bledny scenariusz.

Testuje walidator: sprzeczne obserwacje, nakladanie akcji (Z2),
naruszenie impossible_at (Z8).
"""

from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    CausesStatement, DurationStatement, ImpossibleAtStatement,
    AtomicFormula, Negation,
)
from src.examples.helpers import (
    print_domain, print_scenario, print_validation,
)


def run():
    print("\n" + "=" * 60)
    print("  PRZYKLAD 3: Bledny scenariusz (test walidacji)")
    print("=" * 60)
    print("""
Co pokazuje:
  Dzialanie walidatora scenariuszy. Scenariusz zawiera celowo wiele
  naruszen zalozen DS1:
    - sprzeczne obserwacje (broken i ~broken w tej samej chwili t=0),
    - nakladajace sie akcje w ACS (narusza Z2 sekwencyjnosci),
    - akcja zadeklarowana w punkcie 'impossible at' (narusza Z8).
  Walidator powinien odrzucic scenariusz przed rozwiazywaniem.
""")

    # Dziedzina:
    #   repair duration 3
    #   reboot duration 2
    #   reboot causes system_on after 2 if ~broken
    #   impossible reboot at 0
    domain = Domain(
        durations=[
            DurationStatement("repair", 3),
            DurationStatement("reboot", 2),
        ],
        causes=[
            CausesStatement(
                "reboot",
                AtomicFormula("system_on"),
                2,
                Negation(AtomicFormula("broken")),
            ),
        ],
        impossible_at=[ImpossibleAtStatement("reboot", 0)],
    )

    # Scenariusz (celowo bledny):
    #   OBS: (broken, 0), (~broken, 0)               <- sprzecznosc
    #   ACS: (repair, 0), (reboot, 1), (reboot, 0)   <- nakladanie + impossible_at
    scenario = Scenario(
        observations=[
            Observation(AtomicFormula("broken"), 0),
            Observation(Negation(AtomicFormula("broken")), 0),
        ],
        action_declarations=[
            ActionDeclaration("repair", 0),
            ActionDeclaration("reboot", 1),
            ActionDeclaration("reboot", 0),
        ],
    )

    print_domain(domain)
    print_scenario(scenario)

    if not print_validation(domain, scenario):
        print("\nScenariusz odrzucony — nie spelnia zalozen DS1.")
        return
