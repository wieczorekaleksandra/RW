"""Parser tekstowego formatu DS1.

Format pliku:

    # Komentarze (linie zaczynajace sie od #) sa ignorowane.

    DOMAIN:
    <instrukcje, kazda w osobnej linii>

    SCENARIO:
    OBS:
    (formula, t)
    ...
    ACS:
    (action, t)
    ...

    QUERIES:
    <kwerendy, kazda w osobnej linii>

Instrukcje dziedziny:
    <action> duration <int>
    <action> causes <formula> after <int> [if <formula>]
    <action> releases <fluent> during [<int>,<int>]
    <action> triggers <action> after <int>
    <formula> causes <action>                 # state trigger
    impossible <action> if <formula>
    impossible <action> at <int>

Formuly: ~ (negacja), & (koniunkcja), | (alternatywa), nawiasy do grupowania.
Precedencja od najwyzszej: ~ > & > |
"""

import re

from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    CausesStatement, DurationStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement,
    ImpossibleIfStatement, ImpossibleAtStatement,
    AtomicFormula, Negation, Conjunction, Disjunction,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)


class ParseError(Exception):
    pass


# ============================================================
# Publiczne API
# ============================================================

def parse_file(path):
    """Wczytuje plik .txt i zwraca (domain, scenario, queries).

    queries to lista par (etykieta, query_obj) dla zachowania
    oryginalnego napisu w GUI/CLI.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return parse_text(f.read())


def parse_text(content):
    """Parsuj zawartosc tekstowa pliku."""
    sections = _split_sections(content)
    domain = _parse_domain(sections.get('DOMAIN', ''))
    scenario = _parse_scenario(sections.get('SCENARIO', ''))
    queries = _parse_queries(sections.get('QUERIES', ''))
    return domain, scenario, queries


def derive_fluents_actions(domain, scenario, queries=()):
    """Wyciaga (fluents, actions) wystepujace w domenie/scenariuszu/kwerendach.

    Zwraca dwie posortowane listy.
    """
    from src.formula_eval import get_fluents

    fluents = set()
    actions = set()

    for c in domain.causes:
        fluents |= get_fluents(c.effect)
        if c.condition:
            fluents |= get_fluents(c.condition)
        actions.add(c.action)
    for r in domain.releases:
        fluents.add(r.fluent)
        actions.add(r.action)
    for st in domain.state_triggers:
        fluents |= get_fluents(st.condition)
        actions.add(st.action)
    for imp in domain.impossible_if:
        fluents |= get_fluents(imp.condition)
        actions.add(imp.action)
    for imp in domain.impossible_at:
        actions.add(imp.action)
    for d in domain.durations:
        actions.add(d.action)
    for tr in domain.triggers:
        actions.add(tr.cause_action)
        actions.add(tr.triggered_action)
    for obs in scenario.observations:
        fluents |= get_fluents(obs.formula)
    for ad in scenario.action_declarations:
        actions.add(ad.action)
    for _, q in queries:
        if isinstance(q, QueryPerforming):
            actions.add(q.action)
        elif isinstance(q, QueryCondition):
            fluents |= get_fluents(q.formula)

    return sorted(fluents), sorted(actions)


# ============================================================
# Sekcje
# ============================================================

_SECTION_NAMES = ('DOMAIN', 'SCENARIO', 'QUERIES')


def _split_sections(content):
    """Podziel zawartosc na DOMAIN/SCENARIO/QUERIES. Pomija komentarze (#)."""
    sections = {}
    current = None
    lines = []

    for raw_line in content.split('\n'):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        upper = stripped.upper().rstrip(':')
        if upper in _SECTION_NAMES:
            if current is not None:
                sections[current] = '\n'.join(lines)
            current = upper
            lines = []
        else:
            lines.append(raw_line)

    if current is not None:
        sections[current] = '\n'.join(lines)

    return sections


# ============================================================
# Dziedzina
# ============================================================

_DURATION_RE = re.compile(r'^(\w+)\s+duration\s+(\d+)$')
_RELEASES_RE = re.compile(
    r'^(\w+)\s+releases\s+(\w+)\s+during\s+\[\s*(\d+)\s*,\s*(\d+)\s*\]$'
)
_TRIGGERS_RE = re.compile(r'^(\w+)\s+triggers\s+(\w+)\s+after\s+(\d+)$')
_IMPOSSIBLE_IF_RE = re.compile(r'^impossible\s+(\w+)\s+if\s+(.+)$')
_IMPOSSIBLE_AT_RE = re.compile(r'^impossible\s+(\w+)\s+at\s+(\d+)$')
_AFTER_IF_RE = re.compile(r'^(.+?)\s+after\s+(\d+)(?:\s+if\s+(.+))?$')
_IDENTIFIER_RE = re.compile(r'^[A-Za-z_]\w*$')


def _parse_domain(text):
    """Parsuj sekcje DOMAIN i zwroc Domain."""
    durations = []
    causes = []
    releases = []
    triggers = []
    state_triggers = []
    impossible_if = []
    impossible_at = []

    for line_no, raw_line in enumerate(text.split('\n'), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            stmt = _parse_domain_line(line)
        except ParseError as e:
            raise ParseError(f"DOMAIN linia {line_no} ('{line}'): {e}")
        if isinstance(stmt, DurationStatement):
            durations.append(stmt)
        elif isinstance(stmt, CausesStatement):
            causes.append(stmt)
        elif isinstance(stmt, ReleasesStatement):
            releases.append(stmt)
        elif isinstance(stmt, TriggersStatement):
            triggers.append(stmt)
        elif isinstance(stmt, StateTriggerStatement):
            state_triggers.append(stmt)
        elif isinstance(stmt, ImpossibleIfStatement):
            impossible_if.append(stmt)
        elif isinstance(stmt, ImpossibleAtStatement):
            impossible_at.append(stmt)

    return Domain(
        durations=durations,
        causes=causes,
        releases=releases,
        triggers=triggers,
        state_triggers=state_triggers,
        impossible_if=impossible_if,
        impossible_at=impossible_at,
    )


def _parse_domain_line(line):
    """Rozpoznaj typ instrukcji i zwroc odpowiedni obiekt."""
    m = _IMPOSSIBLE_AT_RE.match(line)
    if m:
        return ImpossibleAtStatement(m.group(1), int(m.group(2)))
    m = _IMPOSSIBLE_IF_RE.match(line)
    if m:
        return ImpossibleIfStatement(m.group(1), _parse_formula(m.group(2)))

    m = _DURATION_RE.match(line)
    if m:
        return DurationStatement(m.group(1), int(m.group(2)))
    m = _RELEASES_RE.match(line)
    if m:
        return ReleasesStatement(
            m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        )
    m = _TRIGGERS_RE.match(line)
    if m:
        return TriggersStatement(m.group(1), m.group(2), int(m.group(3)))

    # 'causes' moze byc 'a causes <formula> after <delta> [if <pi>]'
    # albo state trigger '<formula> causes <action>'
    if ' causes ' in line:
        left, right = line.split(' causes ', 1)
        m = _AFTER_IF_RE.match(right)
        if m:
            action = left.strip()
            if not _is_identifier(action):
                raise ParseError(
                    f"Po lewej '{action} causes ...' oczekiwano pojedynczej akcji"
                )
            effect = _parse_formula(m.group(1))
            delay = int(m.group(2))
            cond = _parse_formula(m.group(3)) if m.group(3) else None
            return CausesStatement(action, effect, delay, cond)
        # state trigger
        condition = _parse_formula(left)
        action = right.strip()
        if not _is_identifier(action):
            raise ParseError(
                f"Po 'causes' w wyzwalaczu stanowym oczekiwano nazwy akcji, dostalem '{action}'"
            )
        return StateTriggerStatement(condition, action)

    raise ParseError(f"Nierozpoznana instrukcja")


def _is_identifier(s):
    return bool(_IDENTIFIER_RE.match(s))


# ============================================================
# Scenariusz
# ============================================================

def _parse_scenario(text):
    """Parsuj OBS i ACS w sekcji SCENARIO."""
    observations = []
    acs = []
    current = None
    for line_no, raw_line in enumerate(text.split('\n'), 1):
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper().rstrip(':')
        if upper == 'OBS':
            current = 'OBS'
            continue
        if upper == 'ACS':
            current = 'ACS'
            continue
        try:
            if current == 'OBS':
                observations.append(_parse_observation(line))
            elif current == 'ACS':
                acs.append(_parse_acs(line))
            else:
                raise ParseError(
                    "Linia poza sekcja OBS/ACS — dodaj naglowek 'OBS:' lub 'ACS:'"
                )
        except ParseError as e:
            raise ParseError(f"SCENARIO linia {line_no} ('{line}'): {e}")

    return Scenario(observations=observations, action_declarations=acs)


def _parse_observation(line):
    """Parsuj '(formula, t)' -> Observation."""
    inner = _strip_outer_parens(line)
    formula_text, time_text = _split_last_comma(inner)
    return Observation(_parse_formula(formula_text), int(time_text))


def _parse_acs(line):
    """Parsuj '(action, t)' -> ActionDeclaration."""
    inner = _strip_outer_parens(line)
    action_text, time_text = _split_last_comma(inner)
    action = action_text.strip()
    if not _is_identifier(action):
        raise ParseError(f"Oczekiwano nazwy akcji, dostalem '{action}'")
    return ActionDeclaration(action, int(time_text))


def _strip_outer_parens(line):
    if not (line.startswith('(') and line.endswith(')')):
        raise ParseError(f"Oczekiwano '(...)'")
    return line[1:-1].strip()


def _split_last_comma(text):
    idx = text.rfind(',')
    if idx == -1:
        raise ParseError("Brak przecinka")
    return text[:idx].strip(), text[idx + 1:].strip()


# ============================================================
# Kwerendy
# ============================================================

_PERF_RE = re.compile(
    r'^(necessary|possibly)\s+performing\s+(\w+)\s+at\s+(\d+)(?:\s+when\s+Sc)?$'
)
_COND_RE = re.compile(
    r'^(necessary|possibly)\s+(.+?)\s+at\s+(\d+)(?:\s+when\s+Sc)?$'
)


def _parse_queries(text):
    """Parsuj sekcje QUERIES. Zwraca liste (etykieta, query_obj)."""
    queries = []
    for line_no, raw_line in enumerate(text.split('\n'), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            q = _parse_query(line)
        except ParseError as e:
            raise ParseError(f"QUERIES linia {line_no} ('{line}'): {e}")
        queries.append((line, q))
    return queries


def _parse_query(line):
    if line == 'possibly Sc':
        return QueryPossiblyScenario()
    m = _PERF_RE.match(line)
    if m:
        return QueryPerforming(m.group(1), m.group(2), int(m.group(3)))
    m = _COND_RE.match(line)
    if m:
        formula = _parse_formula(m.group(2))
        return QueryCondition(m.group(1), formula, int(m.group(3)))
    raise ParseError(f"Nieznana kwerenda")


# ============================================================
# Parser formul logicznych (recursive descent)
# ============================================================

def _parse_formula(text):
    """Parsuj formule logiczna. Obsluguje ~, &, |, nawiasy."""
    text = text.strip()
    if not text:
        raise ParseError("Pusta formula")
    tokens = _tokenize_formula(text)
    parser = _FormulaParser(tokens)
    result = parser._parse_or()
    if parser.pos != len(tokens):
        tok = tokens[parser.pos]
        raise ParseError(f"Niespodziewany token po formule: '{tok[1]}'")
    return result


def _tokenize_formula(text):
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif c == '~':
            tokens.append(('NOT', '~'))
            i += 1
        elif c == '&':
            tokens.append(('AND', '&'))
            i += 1
        elif c == '|':
            tokens.append(('OR', '|'))
            i += 1
        elif c == '(':
            tokens.append(('LPAREN', '('))
            i += 1
        elif c == ')':
            tokens.append(('RPAREN', ')'))
            i += 1
        elif c.isalpha() or c == '_':
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                j += 1
            tokens.append(('ID', text[i:j]))
            i = j
        else:
            raise ParseError(f"Nieznany znak '{c}' w formule")
    return tokens


class _FormulaParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _parse_or(self):
        left = self._parse_and()
        while self._peek() and self._peek()[0] == 'OR':
            self.pos += 1
            right = self._parse_and()
            left = Disjunction(left, right)
        return left

    def _parse_and(self):
        left = self._parse_not()
        while self._peek() and self._peek()[0] == 'AND':
            self.pos += 1
            right = self._parse_not()
            left = Conjunction(left, right)
        return left

    def _parse_not(self):
        if self._peek() and self._peek()[0] == 'NOT':
            self.pos += 1
            return Negation(self._parse_not())
        return self._parse_atom()

    def _parse_atom(self):
        tok = self._peek()
        if tok is None:
            raise ParseError("Niespodziewany koniec formuly")
        if tok[0] == 'LPAREN':
            self.pos += 1
            expr = self._parse_or()
            if not self._peek() or self._peek()[0] != 'RPAREN':
                raise ParseError("Brak ')'")
            self.pos += 1
            return expr
        if tok[0] == 'ID':
            self.pos += 1
            return AtomicFormula(tok[1])
        raise ParseError(f"Niespodziewany token: '{tok[1]}'")
