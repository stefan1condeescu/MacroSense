from ui.language import translate


MIN_QUANTITY_G = 1.0
MAX_QUANTITY_G = 5000.0


def _quantity_validation_code(quantity) -> str | None:
    try:
        quantity_value = float(quantity)
    except (TypeError, ValueError):
        return "invalid_number"

    if quantity_value < MIN_QUANTITY_G:
        return "below_minimum"
    if quantity_value > MAX_QUANTITY_G:
        return "above_maximum"
    return None


def validate_quantity_g(quantity, field_label: str = "Cantitatea") -> str | None:
    """Returns a Romanian validation error for gram quantities, or None when valid."""
    validation_code = _quantity_validation_code(quantity)
    if validation_code == "invalid_number":
        return f"{field_label} trebuie să fie un număr valid."
    if validation_code == "below_minimum":
        return f"{field_label} trebuie să fie cel puțin {MIN_QUANTITY_G:.0f} g."
    if validation_code == "above_maximum":
        return f"{field_label} trebuie să fie cel mult {MAX_QUANTITY_G:.0f} g."
    return None


def quantity_range_help() -> str:
    """Returns the shared UI help text for gram quantity inputs."""
    return f"Interval acceptat: {MIN_QUANTITY_G:.0f}-{MAX_QUANTITY_G:.0f} g."


def validate_quantity_g_for_ui(
    quantity,
    field_label_source: str = "Quantity",
) -> str | None:
    """Return a bilingual validation error while preserving the numeric rules."""
    field_label = translate(field_label_source)
    validation_code = _quantity_validation_code(quantity)
    if validation_code == "invalid_number":
        return translate(
            "{field_label} must be a valid number.",
            field_label=field_label,
        )
    if validation_code == "below_minimum":
        return translate(
            "{field_label} must be at least {minimum:.0f} g.",
            field_label=field_label,
            minimum=MIN_QUANTITY_G,
        )
    if validation_code == "above_maximum":
        return translate(
            "{field_label} must be at most {maximum:.0f} g.",
            field_label=field_label,
            maximum=MAX_QUANTITY_G,
        )
    return None


def quantity_range_help_for_ui() -> str:
    """Return bilingual help text for the supported gram range."""
    return translate(
        "Accepted range: {minimum:.0f}-{maximum:.0f} g.",
        minimum=MIN_QUANTITY_G,
        maximum=MAX_QUANTITY_G,
    )
