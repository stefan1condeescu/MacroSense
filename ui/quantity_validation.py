MIN_QUANTITY_G = 1.0
MAX_QUANTITY_G = 5000.0


def validate_quantity_g(quantity, field_label: str = "Cantitatea") -> str | None:
    """Returns a Romanian validation error for gram quantities, or None when valid."""
    try:
        quantity_value = float(quantity)
    except (TypeError, ValueError):
        return f"{field_label} trebuie să fie un număr valid."

    if quantity_value < MIN_QUANTITY_G:
        return f"{field_label} trebuie să fie cel puțin {MIN_QUANTITY_G:.0f} g."
    if quantity_value > MAX_QUANTITY_G:
        return f"{field_label} trebuie să fie cel mult {MAX_QUANTITY_G:.0f} g."

    return None


def quantity_range_help() -> str:
    """Returns the shared UI help text for gram quantity inputs."""
    return f"Interval acceptat: {MIN_QUANTITY_G:.0f}-{MAX_QUANTITY_G:.0f} g."
