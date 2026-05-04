"""Shared validation helpers for user-entered text."""


HTML_LIKE_CHARS = ("<", ">")
PERSON_NAME_EXTRA_CHARS = {"-", "'", "’"}


def has_obvious_html_chars(value: str) -> bool:
    """Returns True when text contains characters that can break custom HTML UI."""
    return any(char in (value or "") for char in HTML_LIKE_CHARS)


def contains_letter(value: str) -> bool:
    """Returns True when text contains at least one Unicode alphabetic character."""
    return any(char.isalpha() for char in (value or ""))


def is_valid_catalog_name(value: str) -> bool:
    """Validates food/activity catalog names without blocking useful punctuation."""
    text = (value or "").strip()
    return bool(text) and not has_obvious_html_chars(text) and contains_letter(text)


def is_valid_person_name(value: str) -> bool:
    """Validates persisted full names used in profile UI."""
    text = (value or "").strip()
    if not text or has_obvious_html_chars(text) or not contains_letter(text):
        return False
    return all(
        char.isalpha() or char.isspace() or char in PERSON_NAME_EXTRA_CHARS
        for char in text
    )
