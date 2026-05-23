import datetime
import pandas as pd

def format_time_for_display(value) -> str:
    """Formats database time values for Streamlit display widgets."""
    if value is None:
        return "-"

    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass

    if isinstance(value, datetime.timedelta):
        total_seconds = int(value.total_seconds())
        return (datetime.datetime.min + datetime.timedelta(seconds=total_seconds)).time().strftime("%H:%M")

    if isinstance(value, datetime.time):
        return value.strftime("%H:%M")

    if isinstance(value, str):
        try:
            return datetime.time.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return value

    return str(value)

def format_food_entries_for_display(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Returns a UI-safe copy of food log entries with formatted time."""
    visible_dataframe = dataframe.copy()
    if "Ora" in visible_dataframe.columns:
        visible_dataframe["Ora"] = visible_dataframe["Ora"].apply(format_time_for_display)
    return visible_dataframe


def format_kcal_for_display(value, signed: bool = False) -> str:
    """Formats kcal values consistently across dashboard-adjacent UI sections."""
    if value is None:
        return "-"

    try:
        if pd.isna(value):
            return "-"
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "-"

    if signed:
        return f"{numeric_value:+.0f} kcal"
    return f"{numeric_value:.0f} kcal"
