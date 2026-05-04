MIN_DURATION_MINUTES = 0.1
MAX_DURATION_MINUTES = 600.0
MIN_SETS = 1
MAX_SETS = 50
MIN_REPS = 1
MAX_REPS = 200


def validate_duration_minutes(duration, field_label: str = "Durata") -> str | None:
    """Returns a Romanian validation error for activity duration, or None when valid."""
    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return f"{field_label} trebuie să fie un număr valid."

    if duration_value < MIN_DURATION_MINUTES:
        return f"{field_label} trebuie să fie cel puțin {MIN_DURATION_MINUTES:.1f} minute."
    if duration_value > MAX_DURATION_MINUTES:
        return f"{field_label} trebuie să fie cel mult {MAX_DURATION_MINUTES:.0f} minute."

    return None


def validate_activity_count(value, field_label: str, minimum: int, maximum: int) -> str | None:
    """Returns a Romanian validation error for strength-training counts."""
    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return f"{field_label} trebuie să fie un număr valid."

    if numeric_value < minimum:
        return f"{field_label} trebuie să fie cel puțin {minimum}."
    if numeric_value > maximum:
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
