from models.tracking import ActivityLog
from ui.language import translate


MIN_DURATION_MINUTES = ActivityLog.MIN_DURATION_MINUTES
MAX_DURATION_MINUTES = ActivityLog.MAX_DURATION_MINUTES
MIN_SETS = ActivityLog.MIN_SETS
MAX_SETS = ActivityLog.MAX_SETS
MIN_REPS = ActivityLog.MIN_REPS
MAX_REPS = ActivityLog.MAX_REPS


def _duration_validation_code(duration) -> str | None:
    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return "invalid_number"

    if duration_value < MIN_DURATION_MINUTES:
        return "below_minimum"
    if duration_value > MAX_DURATION_MINUTES:
        return "above_maximum"
    return None


def _activity_count_validation_code(
    value,
    minimum: int,
    maximum: int,
) -> str | None:
    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return "invalid_number"

    if numeric_value < minimum:
        return "below_minimum"
    if numeric_value > maximum:
        return "above_maximum"
    return None


def validate_duration_minutes(duration, field_label: str = "Durata") -> str | None:
    """Returns a Romanian validation error for activity duration, or None when valid."""
    validation_code = _duration_validation_code(duration)
    if validation_code == "invalid_number":
        return f"{field_label} trebuie să fie un număr valid."
    if validation_code == "below_minimum":
        return f"{field_label} trebuie să fie cel puțin {MIN_DURATION_MINUTES:.1f} minute."
    if validation_code == "above_maximum":
        return f"{field_label} trebuie să fie cel mult {MAX_DURATION_MINUTES:.0f} minute."
    return None


def validate_activity_count(value, field_label: str, minimum: int, maximum: int) -> str | None:
    """Returns a Romanian validation error for strength-training counts."""
    validation_code = _activity_count_validation_code(value, minimum, maximum)
    if validation_code == "invalid_number":
        return f"{field_label} trebuie să fie un număr valid."
    if validation_code == "below_minimum":
        return f"{field_label} trebuie să fie cel puțin {minimum}."
    if validation_code == "above_maximum":
        return f"{field_label} trebuie să fie cel mult {maximum}."
    return None


def validate_sets(sets) -> str | None:
    """Validates strength-training sets for the Activity Journal UI."""
    return validate_activity_count(sets, "Seturile", MIN_SETS, MAX_SETS)


def validate_reps(reps) -> str | None:
    """Validates strength-training reps for the Activity Journal UI."""
    return validate_activity_count(reps, "Repetările", MIN_REPS, MAX_REPS)


def duration_range_help() -> str:
    """Returns the shared UI help text for activity duration inputs."""
    return f"Interval acceptat: {MIN_DURATION_MINUTES:.1f}-{MAX_DURATION_MINUTES:.0f} minute."


def validate_duration_minutes_for_ui(
    duration,
    field_label_source: str = "Duration",
) -> str | None:
    """Return a bilingual duration error while preserving the numeric rules."""
    field_label = translate(field_label_source)
    validation_code = _duration_validation_code(duration)
    if validation_code == "invalid_number":
        return translate(
            "{field_label} must be a valid number.",
            field_label=field_label,
        )
    if validation_code == "below_minimum":
        return translate(
            "{field_label} must be at least {minimum:.1f} minutes.",
            field_label=field_label,
            minimum=MIN_DURATION_MINUTES,
        )
    if validation_code == "above_maximum":
        return translate(
            "{field_label} must be at most {maximum:.0f} minutes.",
            field_label=field_label,
            maximum=MAX_DURATION_MINUTES,
        )
    return None


def validate_activity_count_for_ui(
    value,
    field_label_source: str,
    minimum: int,
    maximum: int,
) -> str | None:
    """Return a bilingual strength-count error while preserving its limits."""
    field_label = translate(field_label_source)
    validation_code = _activity_count_validation_code(value, minimum, maximum)
    if validation_code == "invalid_number":
        return translate(
            "{field_label} must be a valid number.",
            field_label=field_label,
        )
    if validation_code == "below_minimum":
        return translate(
            "{field_label} must be at least {minimum}.",
            field_label=field_label,
            minimum=minimum,
        )
    if validation_code == "above_maximum":
        return translate(
            "{field_label} must be at most {maximum}.",
            field_label=field_label,
            maximum=maximum,
        )
    return None


def validate_sets_for_ui(sets) -> str | None:
    """Validate sets with a label for the active UI language."""
    return validate_activity_count_for_ui(
        sets,
        "Set count",
        MIN_SETS,
        MAX_SETS,
    )


def validate_reps_for_ui(reps) -> str | None:
    """Validate repetitions with a label for the active UI language."""
    return validate_activity_count_for_ui(
        reps,
        "Repetition count",
        MIN_REPS,
        MAX_REPS,
    )


def duration_range_help_for_ui() -> str:
    """Return bilingual help text for the supported duration range."""
    return translate(
        "Accepted range: {minimum:.1f}-{maximum:.0f} minutes.",
        minimum=MIN_DURATION_MINUTES,
        maximum=MAX_DURATION_MINUTES,
    )
