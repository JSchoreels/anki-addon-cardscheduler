"""Context-sensitive ambiguity factors for kanji reading families."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .dictionary import (
    expand_iteration_marks,
    extract_kanji_only,
    get_rendaku_form,
    get_rendaku_form_p,
    get_sokuon_form,
    load_kanji_dictionnary_readings,
)
from .sentence_morphology import MecabTokenAnalyzer, SurfaceToken, katakana_to_hiragana
from .word_parser import extract_kana_readings, split_reading_with_positions


logger = logging.getLogger(__name__)

PAIR_PATTERN = re.compile(r"([一-龯ぁ-ゖァ-ヺー々]+)\[([^\]]+)\]([ぁ-ゖァ-ヺー]*)")
FURIGANA_PATTERN = re.compile(r"\[.*?\]")
VOICED_OBSTRUENTS = set("がぎぐげござじずぜぞだぢづでどばびぶべぼ")
PHRASE_BOUNDARY_POS = {"形容詞", "連体詞", "動詞", "助詞", "助動詞"}
EXPLICIT_BOUNDARY = set(" \t・、。！？,.;:!?()（）[]【】「」『』")
SOKUON_ONSET_ROWS = {
    "K": set("かきくけこ"),
    "S": set("さしすせそ"),
    "T": set("たちつてと"),
    "P": set("ぱぴぷぺぽ"),
}

ENTROPY_STRENGTH = 0.5
CONTEXT_BACKOFF = 3.0
SOKUON_RELIEF_MIN_EVIDENCE = 2
SOKUON_RELIEF_MIN_SHARE = 0.8
SOKUON_RELIEF_SHRINKAGE = 2.0


@dataclass(frozen=True)
class ReadingComponent:
    kanji: str
    actual: str
    canonical: str
    variant_kind: str


@dataclass(frozen=True)
class TokenSpan:
    surface: str
    pos: str
    start: int
    end: int


@dataclass(frozen=True)
class ComponentContext:
    token_initial: bool | None
    token_final: bool | None
    token_pos: str
    rendaku_blocked: bool
    sokuon_blocked: bool
    boundary_kind: str
    sokuon_environment: str

    @property
    def key(self):
        if self.token_initial is None:
            return (
                f"uncertain;rendaku_blocked={self.rendaku_blocked};"
                f"sokuon_blocked={self.sokuon_blocked}"
            )
        return (
            f"token_initial={self.token_initial};token_final={self.token_final};"
            f"pos={self.token_pos};boundary={self.boundary_kind};"
            f"rendaku_blocked={self.rendaku_blocked};"
            f"sokuon_blocked={self.sokuon_blocked}"
        )


def normalize_canonical(reading):
    return (reading or "").split(".", 1)[0].replace("-", "").strip()


def classify_variant(actual, canonical):
    if not actual or not canonical:
        return "unresolved"
    if actual == canonical:
        return "exact"
    if actual in {get_rendaku_form(canonical), get_rendaku_form_p(canonical)}:
        return "rendaku"
    if actual == get_sokuon_form(canonical):
        return "sokuon"
    return "other"


def normalize_actual(actual, canonical):
    """Strip okurigana while preserving a realized rendaku or sokuon form."""
    if not actual or not canonical:
        return actual
    candidates = {
        canonical,
        get_rendaku_form(canonical),
        get_rendaku_form_p(canonical),
        get_sokuon_form(canonical),
    }
    prefixes = [candidate for candidate in candidates if candidate and actual.startswith(candidate)]
    return max(prefixes, key=len) if prefixes else actual


def canonical_for_actual(kanji, actual, kanji_readings):
    readings = kanji_readings.get(kanji, {})
    direct = [
        normalize_canonical(base)
        for base in readings
        if normalize_canonical(base) == actual
    ]
    if direct:
        return max(direct, key=len)

    candidates = []
    for base, variations in readings.items():
        canonical = normalize_canonical(base)
        normalized_variations = {normalize_canonical(value) for value in variations}
        if actual in normalized_variations:
            candidates.append(canonical)
    return max(candidates, key=len) if candidates else actual


def extract_reading_components(text, kanji_readings):
    """Return actual and canonical readings for each parsed kanji component."""
    components = set()
    processed_kanji = set()

    for match in PAIR_PATTERN.finditer(text or ""):
        kanji_word, reading_text, conjugation = match.groups()
        for reading_option in extract_kana_readings(reading_text):
            word_with_conjugation = kanji_word + conjugation
            reading = reading_option + conjugation

            if len(word_with_conjugation) == 1:
                kanji = word_with_conjugation
                actual = reading.strip()
                canonical = canonical_for_actual(kanji, actual, kanji_readings)
                components.add(
                    ReadingComponent(
                        kanji,
                        actual,
                        canonical,
                        classify_variant(actual, canonical),
                    )
                )
                processed_kanji.add(kanji)
                continue

            expanded_word = expand_iteration_marks(word_with_conjugation)
            try:
                reading_parts = split_reading_with_positions(
                    expanded_word,
                    reading,
                    kanji_readings,
                )
            except KeyError:
                reading_parts = []

            for kanji, actual_reading, dictionary_form in reading_parts:
                actual = (actual_reading or "").strip()
                canonical = normalize_canonical(dictionary_form)
                if not canonical and actual:
                    canonical = canonical_for_actual(kanji, actual, kanji_readings)
                actual = normalize_actual(actual, canonical)
                components.add(
                    ReadingComponent(
                        kanji,
                        actual,
                        canonical,
                        classify_variant(actual, canonical),
                    )
                )
                processed_kanji.add(kanji)

    for kanji in extract_kanji_only(text or ""):
        if kanji not in processed_kanji:
            components.add(ReadingComponent(kanji, "", "", "unresolved"))

    return components


def card_surface(card):
    if card.word_surface:
        return card.word_surface
    return FURIGANA_PATTERN.sub("", card.furigana_text or "").strip()


def build_token_spans(surface, tokens):
    cursor = 0
    spans = []
    for token in tokens:
        start = surface.find(token.surface, cursor)
        if start < 0:
            return []
        end = start + len(token.surface)
        spans.append(TokenSpan(token.surface, token.pos, start, end))
        cursor = end
    return spans


def component_positions(surface, components):
    positions = {}
    for component in components:
        indexes = [index for index, char in enumerate(surface) if char == component.kanji]
        positions[component] = indexes[0] if len(indexes) == 1 else None
    return positions


def onset_row(reading):
    reading = katakana_to_hiragana(reading or "")
    if not reading:
        return "boundary"
    first = reading[0]
    for row, kana in SOKUON_ONSET_ROWS.items():
        if first in kana:
            return row
    return "other"


def _next_component(component, positions):
    index = positions.get(component)
    if index is None:
        return None
    following = [
        (position, candidate)
        for candidate, position in positions.items()
        if position is not None and position > index
    ]
    if not following:
        return None
    next_position = min(position for position, _ in following)
    candidates = [candidate for position, candidate in following if position == next_position]
    return candidates[0] if len(candidates) == 1 else None


def component_context(surface, component, positions, spans):
    index = positions.get(component)
    if index is None:
        return ComponentContext(None, None, "", False, False, "uncertain", "uncertain")

    token_index = next(
        (position for position, span in enumerate(spans) if span.start <= index < span.end),
        None,
    )
    token = spans[token_index] if token_index is not None else None
    token_initial = index == token.start if token else None
    token_final = index == token.end - 1 if token else None
    previous_token = (
        spans[token_index - 1]
        if token_index is not None and token_index > 0 and token_initial
        else None
    )
    following_token = (
        spans[token_index + 1]
        if token_index is not None and token_index + 1 < len(spans) and token_final
        else None
    )

    gap_before = (
        surface[previous_token.end:token.start]
        if token and previous_token
        else surface[: token.start if token else index]
    )
    gap_after = (
        surface[token.end:following_token.start]
        if token and following_token
        else surface[(token.end if token else index + 1):]
    )

    if index == 0:
        boundary_kind = "word_start"
        rendaku_blocked = True
    elif token_initial and previous_token and previous_token.pos in PHRASE_BOUNDARY_POS:
        boundary_kind = f"phrase_after_{previous_token.pos}"
        rendaku_blocked = True
    elif token_initial and any(char in EXPLICIT_BOUNDARY for char in gap_before):
        boundary_kind = "explicit_before"
        rendaku_blocked = True
    elif token_initial:
        boundary_kind = "bare_token_boundary"
        rendaku_blocked = False
    elif token:
        boundary_kind = "inside_token"
        rendaku_blocked = False
    else:
        boundary_kind = "uncertain"
        rendaku_blocked = any(char in EXPLICIT_BOUNDARY for char in gap_before)

    next_component = _next_component(component, positions)
    next_index = positions.get(next_component) if next_component else None
    next_row = onset_row(next_component.actual if next_component else "")
    same_token = bool(
        token and next_index is not None and token.start <= next_index < token.end
    )
    sokuon_environment = f"same:{next_row}" if same_token else "boundary"

    if index == len(surface) - 1:
        sokuon_blocked = True
    elif next_component and next_row not in SOKUON_ONSET_ROWS:
        sokuon_blocked = True
    elif next_component and token and not same_token:
        sokuon_blocked = True
    elif token_final and following_token and following_token.pos in {
        "助詞",
        "助動詞",
        "記号",
        "補助記号",
    }:
        sokuon_blocked = True
    elif token_final and any(char in EXPLICIT_BOUNDARY for char in gap_after):
        sokuon_blocked = True
    else:
        sokuon_blocked = False

    return ComponentContext(
        token_initial,
        token_final,
        token.pos if token else "",
        rendaku_blocked,
        sokuon_blocked,
        boundary_kind,
        sokuon_environment,
    )


def entropy_factor(counts, strength=ENTROPY_STRENGTH):
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 1.0
    proportions = [count / total for count in counts.values() if count > 0]
    entropy = -sum(proportion * math.log(proportion) for proportion in proportions)
    effective_forms = math.exp(entropy)
    return math.exp(-strength * (effective_forms - 1.0))


def _has_medial_voiced_obstruent(canonical):
    return any(kana in VOICED_OBSTRUENTS for kana in (canonical or "")[1:])


def allowed_forms(component, context, family_counts):
    allowed = set()
    lyman_blocked = _has_medial_voiced_obstruent(component.canonical)
    for actual in family_counts:
        kind = classify_variant(actual, component.canonical)
        if kind == "rendaku" and (context.rendaku_blocked or lyman_blocked):
            continue
        if kind == "sokuon" and context.sokuon_blocked:
            continue
        allowed.add(actual)

    # Tokenization and dictionary alignment are fallible. The target card's
    # printed reading is always a possible realization for that card.
    if component.actual:
        allowed.add(component.actual)
    return allowed


def contextual_factor(component, context, family_counts, context_counts):
    allowed = allowed_forms(component, context, family_counts)
    global_allowed = Counter(
        {
            actual: count
            for actual, count in family_counts.items()
            if actual in allowed
        }
    )
    if len(global_allowed) <= 1:
        return entropy_factor(global_allowed)

    global_total = sum(global_allowed.values())
    global_proportions = {
        actual: count / global_total for actual, count in global_allowed.items()
    }
    local = Counter(
        {
            actual: count
            for actual, count in context_counts.items()
            if actual in allowed
        }
    )
    smoothed = Counter(
        {
            actual: local.get(actual, 0) + CONTEXT_BACKOFF * global_proportions[actual]
            for actual in global_allowed
        }
    )
    return entropy_factor(smoothed)


def apply_sokuon_relief(component, context, factor, family_counts, local_counts):
    if not context.sokuon_environment.startswith("same:"):
        return factor
    if component.variant_kind not in {"exact", "sokuon"}:
        return factor
    if not any(
        classify_variant(actual, component.canonical) == "sokuon"
        for actual in family_counts
    ):
        return factor

    evidence = sum(local_counts.values())
    if evidence < SOKUON_RELIEF_MIN_EVIDENCE:
        return factor
    target_share = local_counts.get(component.actual, 0) / evidence
    if target_share < SOKUON_RELIEF_MIN_SHARE:
        return factor

    local_factor = entropy_factor(local_counts)
    reliability = evidence / (evidence + SOKUON_RELIEF_SHRINKAGE)
    blended = math.exp(
        (1.0 - reliability) * math.log(max(factor, 1e-12))
        + reliability * math.log(max(local_factor, 1e-12))
    )
    return max(factor, blended)


def compute_reading_ambiguity_factors(cards, kanji_readings=None, analyzer=None):
    """Return a persistent, context-relieved ambiguity factor per card."""
    if not cards:
        return {}

    kanji_readings = kanji_readings or load_kanji_dictionnary_readings()
    analyzer = analyzer or MecabTokenAnalyzer()
    surfaces = {card.card_id: card_surface(card) for card in cards}
    components = {
        card.card_id: extract_reading_components(card.furigana_text, kanji_readings)
        for card in cards
    }

    if analyzer.available:
        tokens_by_surface = analyzer.extract_surface_tokens_many(surfaces.values())
    else:
        tokens_by_surface = {surface: [] for surface in surfaces.values()}

    spans_by_surface = {
        surface: build_token_spans(surface, tokens_by_surface.get(surface, []))
        for surface in dict.fromkeys(surfaces.values())
    }
    positions = {
        card.card_id: component_positions(surfaces[card.card_id], components[card.card_id])
        for card in cards
    }
    contexts = {
        card.card_id: {
            component: component_context(
                surfaces[card.card_id],
                component,
                positions[card.card_id],
                spans_by_surface.get(surfaces[card.card_id], []),
            )
            for component in components[card.card_id]
        }
        for card in cards
    }

    family_counts = defaultdict(Counter)
    seen_family = set()
    context_counts = defaultdict(Counter)
    seen_context = set()
    sokuon_counts = defaultdict(Counter)
    seen_sokuon = set()

    for card in cards:
        surface = surfaces[card.card_id]
        for component, context in contexts[card.card_id].items():
            if not component.actual or not component.canonical:
                continue
            family = (component.kanji, component.canonical)

            family_key = (family, component.actual, surface)
            if family_key not in seen_family:
                seen_family.add(family_key)
                family_counts[family][component.actual] += 1

            context_key = (family, context.key, component.actual, surface)
            if context_key not in seen_context:
                seen_context.add(context_key)
                context_counts[(family, context.key)][component.actual] += 1

            if component.variant_kind in {"exact", "sokuon"}:
                sokuon_key = (
                    family,
                    context.sokuon_environment,
                    component.actual,
                    surface,
                )
                if sokuon_key not in seen_sokuon:
                    seen_sokuon.add(sokuon_key)
                    sokuon_counts[(family, context.sokuon_environment)][component.actual] += 1

    factors = {}
    affected = 0
    for card in cards:
        component_factors = []
        for component, context in contexts[card.card_id].items():
            if not component.actual or not component.canonical:
                continue
            family = (component.kanji, component.canonical)
            factor = contextual_factor(
                component,
                context,
                family_counts.get(family, Counter()),
                context_counts.get((family, context.key), Counter()),
            )
            factor = apply_sokuon_relief(
                component,
                context,
                factor,
                family_counts.get(family, Counter()),
                sokuon_counts.get((family, context.sokuon_environment), Counter()),
            )
            component_factors.append(factor)

        card_factor = min(component_factors, default=1.0)
        factors[card.card_id] = card_factor
        if card_factor < 0.9995:
            affected += 1

    logger.info(
        "Computed reading ambiguity for %s cards (%s affected, MeCab=%s)",
        len(cards),
        affected,
        analyzer.available,
    )
    return factors
