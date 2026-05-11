import re
from src.models import (
    AtomicFormula, Negation, Conjunction, Disjunction, Implication, Equivalence,
    CausesStatement, DurationStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement,
    ImpossibleIfStatement, ImpossibleAtStatement,
    Domain, Observation, ActionDeclaration, Scenario,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)


# ========================= PARSER FORMUL =========================

def parse_formula(text: str):
    """
    Parsuje formule logiczna.
    Operatory (od najnizszego priorytetu):
      <->   rownowaznosc
      ->    implikacja
      |     alternatywa
      &     koniunkcja
      ~     negacja (prefix)
    Nawiasy () do grupowania.
    """
    text = text.strip()
    tokens = _tokenize(text)
    pos = [0]  # mutable index
    result = _parse_equivalence(tokens, pos)
    return result


def _tokenize(text):
    """Rozbija tekst na tokeny."""
    tokens = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
        elif text[i] == '~':
            tokens.append('~')
            i += 1
        elif text[i] == '&':
            tokens.append('&')
            i += 1
        elif text[i] == '|':
            tokens.append('|')
            i += 1
        elif text[i] == '(':
            tokens.append('(')
            i += 1
        elif text[i] == ')':
            tokens.append(')')
            i += 1
        elif text[i:i+3] == '<->':
            tokens.append('<->')
            i += 3
        elif text[i:i+2] == '->':
            tokens.append('->')
            i += 2
        elif text[i].isalnum() or text[i] == '_':
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                j += 1
            tokens.append(text[i:j])
            i = j
        else:
            raise ValueError(f"Nieoczekiwany znak: '{text[i]}' w formule: {text}")
    return tokens


def _parse_equivalence(tokens, pos):
    left = _parse_implication(tokens, pos)
    while pos[0] < len(tokens) and tokens[pos[0]] == '<->':
        pos[0] += 1
        right = _parse_implication(tokens, pos)
        left = Equivalence(left, right)
    return left


def _parse_implication(tokens, pos):
    left = _parse_disjunction(tokens, pos)
    while pos[0] < len(tokens) and tokens[pos[0]] == '->':
        pos[0] += 1
        right = _parse_disjunction(tokens, pos)
        left = Implication(left, right)
    return left


def _parse_disjunction(tokens, pos):
    left = _parse_conjunction(tokens, pos)
    while pos[0] < len(tokens) and tokens[pos[0]] == '|':
        pos[0] += 1
        right = _parse_conjunction(tokens, pos)
        left = Disjunction(left, right)
    return left


def _parse_conjunction(tokens, pos):
    left = _parse_negation(tokens, pos)
    while pos[0] < len(tokens) and tokens[pos[0]] == '&':
        pos[0] += 1
        right = _parse_negation(tokens, pos)
        left = Conjunction(left, right)
    return left


def _parse_negation(tokens, pos):
    if pos[0] < len(tokens) and tokens[pos[0]] == '~':
        pos[0] += 1
        operand = _parse_negation(tokens, pos)
        return Negation(operand)
    return _parse_atom(tokens, pos)


def _parse_atom(tokens, pos):
    if pos[0] >= len(tokens):
        raise ValueError("Nieoczekiwany koniec formuly")
    token = tokens[pos[0]]
    if token == '(':
        pos[0] += 1
        result = _parse_equivalence(tokens, pos)
        if pos[0] >= len(tokens) or tokens[pos[0]] != ')':
            raise ValueError("Brak zamykajacego nawiasu")
        pos[0] += 1
        return result
    if token not in ('~', '&', '|', '->', '<->', '(', ')'):
        pos[0] += 1
        return AtomicFormula(token)
    raise ValueError(f"Nieoczekiwany token: {token}")


# ========================= PARSER DZIEDZINY =========================

def parse_domain(text: str) -> Domain:
    """Parsuje opis dziedziny — kazda instrukcja w osobnej linii."""
    domain = Domain()
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        _parse_domain_line(line, domain)
    return domain


def _parse_domain_line(line: str, domain: Domain):
    words = line.split()

    # impossible a if α
    if words[0] == 'impossible':
        action = words[1]
        if words[2] == 'if':
            condition = parse_formula(' '.join(words[3:]))
            domain.impossible_if.append(ImpossibleIfStatement(action, condition))
        elif words[2] == 'at':
            domain.impossible_at.append(ImpossibleAtStatement(action, int(words[3])))
        return

    # Sprawdz czy to "formula causes action" (wyzwalacz stanowy)
    # vs "action causes effect after delta ..."
    if 'causes' in words:
        causes_idx = words.index('causes')
        if 'after' in words:
            # a causes α after δ [if π]
            action = words[0]
            after_idx = words.index('after')
            effect_str = ' '.join(words[causes_idx + 1:after_idx])
            effect = parse_formula(effect_str)
            delay = int(words[after_idx + 1])
            condition = None
            if 'if' in words:
                if_idx = words.index('if')
                condition = parse_formula(' '.join(words[if_idx + 1:]))
            domain.causes.append(CausesStatement(action, effect, delay, condition))
        else:
            # Moze byc wyzwalacz stanowy: α causes a
            # Prosta heurystyka: jesli czesc przed "causes" zawiera operatory logiczne
            # lub czesc po "causes" to pojedyncze slowo (nazwa akcji),
            # traktujemy jako wyzwalacz stanowy
            before = ' '.join(words[:causes_idx])
            after = ' '.join(words[causes_idx + 1:])
            # Jesli after to pojedyncze slowo -> wyzwalacz stanowy
            if len(words[causes_idx + 1:]) == 1:
                condition = parse_formula(before)
                domain.state_triggers.append(StateTriggerStatement(condition, after))
            else:
                # Probuj jako causes bez after (efekt natychmiastowy?)
                action = words[0]
                effect = parse_formula(after)
                domain.causes.append(CausesStatement(action, effect, 0))
        return

    # a duration d
    if 'duration' in words:
        action = words[0]
        dur_idx = words.index('duration')
        duration = int(words[dur_idx + 1])
        domain.durations.append(DurationStatement(action, duration))
        return

    # a releases f during [ta, tb]
    if 'releases' in words:
        action = words[0]
        rel_idx = words.index('releases')
        fluent = words[rel_idx + 1]
        # Szukamy [ta, tb] lub [ta,tb]
        rest = ' '.join(words[rel_idx + 2:])
        match = re.search(r'\[(\d+)\s*,\s*(\d+)\]', rest)
        if match:
            ta, tb = int(match.group(1)), int(match.group(2))
            domain.releases.append(ReleasesStatement(action, fluent, ta, tb))
        return

    # a triggers a' after δ
    if 'triggers' in words:
        action = words[0]
        trig_idx = words.index('triggers')
        triggered = words[trig_idx + 1]
        after_idx = words.index('after')
        delay = int(words[after_idx + 1])
        domain.triggers.append(TriggersStatement(action, triggered, delay))
        return

    raise ValueError(f"Nie rozpoznano instrukcji: {line}")


# ========================= PARSER SCENARIUSZA =========================

def parse_scenario(text: str) -> Scenario:
    """
    Parsuje scenariusz. Format:
      OBS:
      (formula, czas)
      (formula, czas)
      ACS:
      (akcja, czas)
    """
    scenario = Scenario()
    section = None

    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.upper().startswith('OBS'):
            section = 'obs'
            continue
        if line.upper().startswith('ACS'):
            section = 'acs'
            continue

        # Parsuj wpis (cos, liczba)
        match = re.match(r'\((.+),\s*(\d+)\)', line)
        if not match:
            continue

        content = match.group(1).strip()
        time = int(match.group(2))

        if section == 'obs':
            formula = parse_formula(content)
            scenario.observations.append(Observation(formula, time))
        elif section == 'acs':
            scenario.action_declarations.append(ActionDeclaration(content, time))

    return scenario


# ========================= PARSER KWEREND =========================

def parse_query(text: str):
    """
    Parsuje kwerendę. Formaty:
      possibly Sc
      necessary performing ACTION at TIME when Sc
      possibly performing ACTION at TIME when Sc
      necessary FORMULA at TIME when Sc
      possibly FORMULA at TIME when Sc
    """
    text = text.strip()

    # possibly Sc
    if re.match(r'^possibly\s+Sc$', text, re.IGNORECASE):
        return QueryPossiblyScenario()

    # necessary/possibly performing ACTION at TIME when Sc
    m = re.match(
        r'(necessary|possibly)\s+performing\s+(\w+)\s+at\s+(\d+)\s+when\s+Sc$',
        text, re.IGNORECASE
    )
    if m:
        return QueryPerforming(m.group(1).lower(), m.group(2), int(m.group(3)))

    # necessary/possibly FORMULA at TIME when Sc
    m = re.match(
        r'(necessary|possibly)\s+(.+?)\s+at\s+(\d+)\s+when\s+Sc$',
        text, re.IGNORECASE
    )
    if m:
        formula = parse_formula(m.group(2))
        return QueryCondition(m.group(1).lower(), formula, int(m.group(3)))

    raise ValueError(f"Nie rozpoznano kwerendy: {text}")
