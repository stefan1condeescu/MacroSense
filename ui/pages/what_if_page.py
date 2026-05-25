from __future__ import annotations

import copy
import hashlib
import html
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from models.tracking import Activity, ActivityLog, CustomMeal, DailyLog, FoodItem, WeightLog
from services.analytics.dashboard_data import get_daily_energy_estimate
from services.what_if.loaders import (
    fetch_activity_scenario_rows,
    fetch_food_scenario_rows,
)
from services.what_if.simulator import (
    WhatIfActivityEntry,
    WhatIfFoodEntry,
    build_activity_entry,
    build_custom_meal_entry,
    build_food_entry,
    calculate_repeated_daily_weight_impact,
    calculate_totals,
    compare_totals,
    describe_balance_delta,
    scenario_matches_real_day,
)
from ui.activity_selection import (
    build_activity_selection_dataframe,
    build_activity_selection_state_key,
    get_activity_category_filter_options,
)
from ui.activity_validation import (
    duration_range_help,
    validate_duration_minutes,
    validate_reps,
    validate_sets,
)
from ui.food_selection import (
    build_food_selection_dataframe,
    build_food_selection_state_key,
    get_food_category_filter_options,
)
from ui.formatters import format_kcal_for_display, format_time_for_display
from ui.quantity_validation import quantity_range_help, validate_quantity_g
from ui.tables import get_table_height


WHAT_IF_CONTEXT_KEY = "what_if_context"
WHAT_IF_FOOD_ROWS_KEY = "what_if_food_rows"
WHAT_IF_ACTIVITY_ROWS_KEY = "what_if_activity_rows"
WHAT_IF_COUNTER_KEY = "what_if_counter"
WHAT_IF_FORCE_RESET_KEY = "what_if_force_reset"
WHAT_IF_LAST_VALID_CONTEXT_KEY = "what_if_last_valid_context"
WHAT_IF_LAST_VALID_COMPARISON_KEY = "what_if_last_valid_comparison"
WHAT_IF_WIDGET_VERSION_KEY = "what_if_widget_version"
WHAT_IF_WIDGET_RESET_KEYS = (
    "what_if_food_search",
    "what_if_food_category_filter",
    "what_if_add_food_quantity",
    "what_if_custom_meal_select",
    "what_if_add_custom_meal_quantity",
    "what_if_activity_search",
    "what_if_activity_category_filter",
    "what_if_add_activity_duration",
    "what_if_add_activity_sets",
    "what_if_add_activity_reps",
    "what_if_add_activity_manual_toggle",
    "what_if_add_activity_manual",
)
WHAT_IF_WIDGET_RESET_PREFIXES = (
    "what_if_food_quantity_",
    "what_if_food_search_",
    "what_if_food_category_filter_",
    "what_if_food_selection_table_",
    "what_if_add_food_quantity_",
    "what_if_custom_meal_select_",
    "what_if_add_custom_meal_quantity_",
    "what_if_activity_duration_",
    "what_if_activity_sets_",
    "what_if_activity_reps_",
    "what_if_activity_manual_toggle_",
    "what_if_activity_manual_",
    "what_if_activity_search_",
    "what_if_activity_category_filter_",
    "what_if_activity_selection_table_",
    "what_if_add_activity_duration_",
    "what_if_add_activity_sets_",
    "what_if_add_activity_reps_",
    "what_if_add_activity_manual_toggle_",
    "what_if_add_activity_manual_",
)
REFERENCE_CONTEXT_COLUMN_WEIGHTS = [2, 0.01, 1, 1]
UNAVAILABLE_RESULT_VALUE = "—"
FOOD_SCENARIO_METADATA_FIELDS = (
    "entry_type",
    "label",
    "meal_type",
    "meal_time",
    "source_label",
    "is_existing",
)
ACTIVITY_SCENARIO_METADATA_FIELDS = (
    "label",
    "category",
    "source_label",
    "is_existing",
)


def render_what_if_page() -> None:
    st.title("🧪 Simulator What-if")
    st.caption(
        "Simulează schimbări pentru o zi fără să modifici jurnalul real. "
        "Pentru schimbări reale, folosește Jurnal Alimentar sau Jurnal Activități."
    )

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning("Autentifică-te pentru a folosi simulatorul.")
        return

    selected_date = st.date_input(
        "Data analizată",
        value=date.today(),
        max_value=date.today(),
        key="what_if_selected_date",
    )
    if isinstance(selected_date, tuple):
        selected_date = selected_date[0]

    daily_log = DailyLog.get_for_date(int(user_id), selected_date)
    real_food_rows = fetch_food_scenario_rows(daily_log.id, int(user_id)) if daily_log else []
    real_activity_rows = (
        fetch_activity_scenario_rows(daily_log.id, int(user_id)) if daily_log else []
    )
    _sync_scenario_state(
        user_id=int(user_id),
        selected_date=selected_date,
        real_food_rows=real_food_rows,
        real_activity_rows=real_activity_rows,
    )

    weight_info = WeightLog.get_reference_for_user(int(user_id), selected_date)
    reference_weight = float(weight_info.get("weight") or 70.0)
    energy_estimate = get_daily_energy_estimate(int(user_id), selected_date)
    base_tdee = energy_estimate.get("base_tdee")
    _render_reference_context(daily_log, reference_weight, weight_info)

    if base_tdee is None:
        st.error(
            "Nu există suficiente date de profil și greutate pentru a calcula TDEE-ul zilei."
        )
        return

    st.divider()
    st.subheader("Construiește scenariul")
    _render_food_scenario_editor()
    _render_add_food_section()
    st.divider()
    _render_activity_scenario_editor(reference_weight)
    _render_add_activity_section(reference_weight)

    real_food_entries, real_activity_entries, real_errors = _build_entries(
        real_food_rows,
        real_activity_rows,
        reference_weight,
    )
    simulated_food_entries, simulated_activity_entries, simulated_errors = _build_entries(
        st.session_state.get(WHAT_IF_FOOD_ROWS_KEY, []),
        st.session_state.get(WHAT_IF_ACTIVITY_ROWS_KEY, []),
        reference_weight,
    )

    errors = real_errors + simulated_errors
    if errors:
        _render_invalid_scenario_result(errors)
        return

    st.divider()
    comparison = compare_totals(
        calculate_totals(real_food_entries, real_activity_entries, base_tdee),
        calculate_totals(simulated_food_entries, simulated_activity_entries, base_tdee),
    )
    _remember_valid_comparison(comparison)
    _render_comparison(comparison)


def _sync_scenario_state(
    user_id: int,
    selected_date: date,
    real_food_rows: list[dict],
    real_activity_rows: list[dict],
) -> None:
    context_key = (
        f"{user_id}:{selected_date.isoformat()}:"
        f"{_scenario_source_fingerprint(real_food_rows, real_activity_rows)}"
    )
    force_reset = bool(st.session_state.pop(WHAT_IF_FORCE_RESET_KEY, False))
    if force_reset or st.session_state.get(WHAT_IF_CONTEXT_KEY) != context_key:
        _reset_scenario_widget_state()
        _clear_last_valid_comparison()
        st.session_state[WHAT_IF_CONTEXT_KEY] = context_key
        food_rows = copy.deepcopy(real_food_rows)
        activity_rows = _prepare_activity_rows(copy.deepcopy(real_activity_rows))
        st.session_state[WHAT_IF_FOOD_ROWS_KEY] = food_rows
        st.session_state[WHAT_IF_ACTIVITY_ROWS_KEY] = activity_rows
        st.session_state[WHAT_IF_COUNTER_KEY] = 0
        _prime_scenario_widget_state(food_rows, activity_rows)
    else:
        _refresh_existing_scenario_metadata(real_food_rows, real_activity_rows)


def _scenario_source_fingerprint(
    real_food_rows: list[dict],
    real_activity_rows: list[dict],
) -> str:
    source_payload = repr(
        [
            (
                row.get("scenario_id"),
                row.get("quantity_g"),
                row.get("calories_100g"),
                row.get("protein_100g"),
                row.get("carbs_100g"),
                row.get("fats_100g"),
            )
            for row in real_food_rows
        ]
        + [
            (
                row.get("scenario_id"),
                row.get("duration_min"),
                row.get("sets"),
                row.get("reps"),
                row.get("manual_calories_burned"),
                row.get("met"),
            )
            for row in real_activity_rows
        ]
    )
    return hashlib.sha1(source_payload.encode("utf-8")).hexdigest()[:12]


def _refresh_existing_scenario_metadata(
    real_food_rows: list[dict],
    real_activity_rows: list[dict],
) -> None:
    _refresh_existing_rows(
        WHAT_IF_FOOD_ROWS_KEY,
        real_food_rows,
        FOOD_SCENARIO_METADATA_FIELDS,
    )
    _refresh_existing_rows(
        WHAT_IF_ACTIVITY_ROWS_KEY,
        real_activity_rows,
        ACTIVITY_SCENARIO_METADATA_FIELDS,
    )


def _refresh_existing_rows(
    session_key: str,
    real_rows: list[dict],
    metadata_fields: tuple[str, ...],
) -> None:
    current_rows = st.session_state.get(session_key, [])
    if not current_rows:
        return

    real_rows_by_id = {row.get("scenario_id"): row for row in real_rows}
    current_rows_by_id = {
        row.get("scenario_id"): row
        for row in current_rows
        if row.get("scenario_id") in real_rows_by_id
    }
    simulated_rows = [
        row for row in current_rows if row.get("scenario_id") not in real_rows_by_id
    ]

    refreshed_rows = []
    for real_row in real_rows:
        current_row = current_rows_by_id.get(real_row.get("scenario_id"))
        if current_row is None:
            continue
        for field in metadata_fields:
            if field in real_row:
                current_row[field] = copy.deepcopy(real_row[field])
        refreshed_rows.append(current_row)

    st.session_state[session_key] = refreshed_rows + simulated_rows


def _clear_scenario_widget_state() -> None:
    for key in list(st.session_state.keys()):
        if key in WHAT_IF_WIDGET_RESET_KEYS or any(
            str(key).startswith(prefix) for prefix in WHAT_IF_WIDGET_RESET_PREFIXES
        ):
            st.session_state.pop(key, None)


def _reset_scenario_widget_state() -> None:
    _clear_scenario_widget_state()
    current_version = int(st.session_state.get(WHAT_IF_WIDGET_VERSION_KEY, 0))
    st.session_state[WHAT_IF_WIDGET_VERSION_KEY] = current_version + 1


def _versioned_widget_key(base_key: str) -> str:
    version = int(st.session_state.get(WHAT_IF_WIDGET_VERSION_KEY, 0))
    return f"{base_key}_{version}"


def _clear_last_valid_comparison() -> None:
    st.session_state.pop(WHAT_IF_LAST_VALID_CONTEXT_KEY, None)
    st.session_state.pop(WHAT_IF_LAST_VALID_COMPARISON_KEY, None)


def _remember_valid_comparison(comparison) -> None:
    st.session_state[WHAT_IF_LAST_VALID_CONTEXT_KEY] = st.session_state.get(
        WHAT_IF_CONTEXT_KEY
    )
    st.session_state[WHAT_IF_LAST_VALID_COMPARISON_KEY] = comparison


def _get_last_valid_comparison():
    if st.session_state.get(WHAT_IF_LAST_VALID_CONTEXT_KEY) != st.session_state.get(
        WHAT_IF_CONTEXT_KEY
    ):
        return None
    return st.session_state.get(WHAT_IF_LAST_VALID_COMPARISON_KEY)


def _number_input_kwargs(key: str, default_value: Any, **kwargs) -> dict:
    widget_kwargs = {**kwargs, "key": key}
    if key not in st.session_state:
        widget_kwargs["value"] = default_value
    return widget_kwargs


def _checkbox_kwargs(key: str, default_value: bool, **kwargs) -> dict:
    widget_kwargs = {**kwargs, "key": key}
    if key not in st.session_state:
        widget_kwargs["value"] = default_value
    return widget_kwargs


def _is_strength_category(category: Any) -> bool:
    return str(category or "").strip() == "Forță"


def _render_inline_validation_message(message: str | None) -> None:
    if not message:
        return
    st.markdown(
        f'<div class="inline-validation-message">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _format_remaining_error_count(count: int) -> str:
    if count == 1:
        return "Încă o valoare invalidă în scenariu."
    return f"Încă {count} valori invalide în scenariu."


def _get_first_error(*errors: str | None) -> str | None:
    return next((error for error in errors if error), None)


def _calculate_food_row_calories(row: dict) -> float | None:
    try:
        entry = build_food_entry(
            entry_id=row.get("scenario_id", "preview"),
            label=row.get("label"),
            entry_type=row.get("entry_type"),
            quantity_g=row.get("quantity_g"),
            calories_100g=row.get("calories_100g"),
            protein_100g=row.get("protein_100g"),
            carbs_100g=row.get("carbs_100g"),
            fats_100g=row.get("fats_100g"),
            source_label=row.get("source_label") or "MacroSense",
            is_existing=row.get("is_existing", False),
        )
    except ValueError:
        return None
    return entry.calories


def _calculate_activity_row_calories(row: dict, reference_weight: float) -> float | None:
    try:
        entry = build_activity_entry(
            entry_id=row.get("scenario_id", "preview"),
            label=row.get("label"),
            category=row.get("category"),
            duration_min=row.get("duration_min"),
            met=row.get("met"),
            weight_kg=reference_weight,
            sets=row.get("sets"),
            reps=row.get("reps"),
            manual_calories_burned=row.get("manual_calories_burned"),
            source_label=row.get("source_label") or "MacroSense",
            is_existing=row.get("is_existing", False),
        )
    except ValueError:
        return None
    return entry.calories_burned


def _render_scenario_row_calories(calories: float | None) -> None:
    st.caption("Calorii")
    if calories is None:
        st.markdown(f"**{UNAVAILABLE_RESULT_VALUE}**")
    else:
        st.markdown(f"**{format_kcal_for_display(calories)}**")


def _render_invalid_scenario_result(errors: list[str]) -> None:
    st.error(errors[0])
    if len(errors) > 1:
        st.caption(_format_remaining_error_count(len(errors) - 1))

    last_valid_comparison = _get_last_valid_comparison()
    if last_valid_comparison is None:
        st.info("Corectează valorile invalide pentru a vedea rezultatul What-if.")
        return

    st.info(
        "Rezultatul de mai jos rămâne ultimul calcul valid; "
        "valorile invalide nu sunt incluse."
    )
    st.divider()
    _render_comparison(last_valid_comparison)


def _prepare_activity_rows(activity_rows: list[dict]) -> list[dict]:
    for row in activity_rows:
        row.setdefault("default_manual_calories_burned", row.get("manual_calories_burned"))
        row.setdefault("last_manual_calories_burned", row.get("manual_calories_burned"))
    return activity_rows


def _prime_scenario_widget_state(food_rows: list[dict], activity_rows: list[dict]) -> None:
    for row in food_rows:
        scenario_id = row["scenario_id"]
        st.session_state[f"what_if_food_quantity_{scenario_id}"] = float(row.get("quantity_g") or 100.0)

    for row in activity_rows:
        scenario_id = row["scenario_id"]
        manual_calories = row.get("manual_calories_burned")
        st.session_state[f"what_if_activity_duration_{scenario_id}"] = float(row.get("duration_min") or 30.0)
        if _is_strength_category(row.get("category")):
            st.session_state[f"what_if_activity_sets_{scenario_id}"] = int(row.get("sets") or 3)
            st.session_state[f"what_if_activity_reps_{scenario_id}"] = int(row.get("reps") or 10)
        st.session_state[f"what_if_activity_manual_toggle_{scenario_id}"] = manual_calories is not None
        if manual_calories is not None:
            st.session_state[f"what_if_activity_manual_{scenario_id}"] = float(manual_calories)


def _render_reference_context(
    daily_log: DailyLog | None,
    reference_weight: float,
    weight_info: dict,
) -> None:
    info_col, spacer_col, weight_col, reset_col = st.columns(REFERENCE_CONTEXT_COLUMN_WEIGHTS)
    with info_col:
        if daily_log:
            st.info("Scenariul pornește de la alimentele și activitățile reale ale zilei.")
        else:
            st.info("Nu există jurnal real pentru această zi. Scenariul pornește de la zero.")
    with spacer_col:
        st.empty()
    with weight_col:
        st.metric("Greutate folosită", f"{reference_weight:.1f} kg")
    with reset_col:
        if st.button(
            "Resetează scenariul",
            key="what_if_reset_button",
            width="stretch",
            type="tertiary",
            help="Revine la valorile reale ale zilei selectate și golește câmpurile de adăugare.",
        ):
            st.session_state[WHAT_IF_FORCE_RESET_KEY] = True
            st.rerun()

    source_date = weight_info.get("source_date")
    if source_date:
        st.caption(
            f"Caloriile activităților sunt calculate cu greutatea de referință din "
            f"{source_date.strftime('%d.%m.%Y')}."
        )
    else:
        st.caption("Nu există cântăriri salvate; simulatorul folosește fallback-ul de 70 kg.")


def _render_food_scenario_editor() -> None:
    st.markdown("**Alimente și mese în scenariu**")
    rows = st.session_state.get(WHAT_IF_FOOD_ROWS_KEY, [])
    if not rows:
        st.info("Scenariul nu conține alimente sau mese.")
        return

    for index, row in enumerate(list(rows)):
        scenario_id = row["scenario_id"]
        source_text = _format_source_context(row)
        with st.container(border=True):
            name_col, calories_col, quantity_col, action_col = st.columns(
                [2.1, 0.85, 1, 0.75],
                vertical_alignment="center",
            )
            with name_col:
                st.markdown(f"**{row.get('label', '-')}**")
                st.caption(source_text)
            with quantity_col:
                quantity_key = f"what_if_food_quantity_{scenario_id}"
                quantity = st.number_input(
                    "Cantitate (g)",
                    **_number_input_kwargs(
                        quantity_key,
                        float(row.get("quantity_g") or 100.0),
                        step=1.0,
                        label_visibility="collapsed",
                        help=quantity_range_help(),
                    ),
                )
                quantity_error = validate_quantity_g(quantity)
                _render_inline_validation_message(quantity_error)
                row["quantity_g"] = float(quantity)
            with calories_col:
                _render_scenario_row_calories(_calculate_food_row_calories(row))
            with action_col:
                if st.button(
                    "Elimină",
                    key=f"what_if_remove_food_{scenario_id}",
                    type="tertiary",
                    width="stretch",
                ):
                    st.session_state[WHAT_IF_FOOD_ROWS_KEY].pop(index)
                    st.rerun()


def _render_add_food_section() -> None:
    with st.expander("Adaugă aliment sau masă doar în scenariu"):
        food_tab, meal_tab = st.tabs(["Aliment catalog", "Masă personalizată"])
        with food_tab:
            _render_add_catalog_food()
        with meal_tab:
            _render_add_custom_meal()


def _render_add_catalog_food() -> None:
    food_options = FoodItem.get_catalog_options()
    if not food_options:
        st.info("Nu există alimente în catalog.")
        return

    search_col, category_col = st.columns([2, 1])
    with search_col:
        search_text = st.text_input(
            "Caută aliment",
            placeholder="Ex: banane, broccoli, pui",
            key=_versioned_widget_key("what_if_food_search"),
        ).strip()
    with category_col:
        category_filter = st.selectbox(
            "Categorie",
            get_food_category_filter_options(food_options),
            key=_versioned_widget_key("what_if_food_category_filter"),
        )

    selection_df = build_food_selection_dataframe(food_options, search_text, category_filter)
    if selection_df.empty:
        st.info("Nu există alimente pentru filtrele selectate.")
        return

    selection_state = st.dataframe(
        selection_df,
        width="stretch",
        height=get_table_height(selection_df, max_rows=8),
        hide_index=True,
        column_order=["Denumire", "Categorie", "Sursă", "Kcal/100g", "Proteine", "Carbohidrați", "Grăsimi"],
        column_config={
            "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
            "Categorie": st.column_config.TextColumn("Categorie", width="small"),
            "Sursă": st.column_config.TextColumn("Sursă", width="small"),
            "Kcal/100g": st.column_config.NumberColumn("Kcal/100g", format="%.1f kcal", width="small"),
            "Proteine": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
            "Carbohidrați": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
            "Grăsimi": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
        },
        key=build_food_selection_state_key(
            search_text,
            category_filter,
            key_prefix=_versioned_widget_key("what_if_food_selection_table"),
        ),
        on_select="rerun",
        selection_mode="single-row",
        row_height=32,
    )
    selected_rows = selection_state.selection.rows
    selected_food_id = None
    if selected_rows and selected_rows[0] < len(selection_df):
        selected_food_id = int(selection_df.iloc[selected_rows[0]]["_food_id"])

    quantity = st.number_input(
        "Cantitate adăugată (g)",
        value=100.0,
        step=10.0,
        help=quantity_range_help(),
        key=_versioned_widget_key("what_if_add_food_quantity"),
    )
    quantity_error = validate_quantity_g(quantity, "Cantitatea adăugată")
    if quantity_error:
        _render_inline_validation_message(quantity_error)

    if st.button(
        "Adaugă aliment în scenariu",
        key="what_if_add_food_button",
        width="stretch",
        type="primary",
    ):
        if selected_food_id is None:
            st.warning("Selectează un aliment din tabel.")
            return
        if quantity_error:
            st.error(quantity_error)
            return
        food = food_options[selected_food_id]
        st.session_state[WHAT_IF_FOOD_ROWS_KEY].append(
            {
                "scenario_id": _next_scenario_id("food"),
                "entry_type": "Aliment",
                "label": food["name"],
                "quantity_g": float(quantity),
                "calories_100g": float(food["calories_100g"]),
                "protein_100g": float(food["protein_g"]),
                "carbs_100g": float(food["carbs_g"]),
                "fats_100g": float(food["fats_g"]),
                "meal_type": "Scenariu",
                "meal_time": None,
                "source_label": food.get("source_label") or "MacroSense",
                "is_existing": False,
            }
        )
        st.rerun()


def _render_add_custom_meal() -> None:
    user_id = int(st.session_state["user_id"])
    meal_options = CustomMeal.get_user_meal_options(user_id, include_archived=False)
    if not meal_options:
        st.info("Nu există mese personalizate active.")
        return

    meal_ids = list(meal_options.keys())
    selected_meal_id = st.selectbox(
        "Masă personalizată",
        meal_ids,
        format_func=lambda meal_id: meal_options[meal_id]["recipe_name"],
        key=_versioned_widget_key("what_if_custom_meal_select"),
    )
    quantity = st.number_input(
        "Cantitate adăugată (g)",
        value=100.0,
        step=10.0,
        help=quantity_range_help(),
        key=_versioned_widget_key("what_if_add_custom_meal_quantity"),
    )
    quantity_error = validate_quantity_g(quantity, "Cantitatea adăugată")
    if quantity_error:
        _render_inline_validation_message(quantity_error)

    if st.button(
        "Adaugă masa în scenariu",
        key="what_if_add_custom_meal_button",
        width="stretch",
        type="primary",
    ):
        if quantity_error:
            st.error(quantity_error)
            return
        selected_meal = meal_options[selected_meal_id]
        try:
            entry = build_custom_meal_entry(
                entry_id=_next_scenario_id("meal"),
                meal=selected_meal,
                quantity_g=quantity,
                is_existing=False,
            )
        except ValueError as exc:
            st.warning(f"Masa selectată nu poate fi simulată: {exc}")
            return
        meal_quantity_g = float(selected_meal["quantity_g"])
        st.session_state[WHAT_IF_FOOD_ROWS_KEY].append(
            {
                "scenario_id": entry.entry_id,
                "entry_type": entry.entry_type,
                "label": entry.label,
                "quantity_g": entry.quantity_g,
                "calories_100g": float(selected_meal["calories"]) * 100.0 / meal_quantity_g,
                "protein_100g": float(selected_meal["protein_g"]) * 100.0 / meal_quantity_g,
                "carbs_100g": float(selected_meal["carbs_g"]) * 100.0 / meal_quantity_g,
                "fats_100g": float(selected_meal["fats_g"]) * 100.0 / meal_quantity_g,
                "meal_type": "Scenariu",
                "meal_time": None,
                "source_label": entry.source_label,
                "is_existing": False,
            }
        )
        st.rerun()


def _render_activity_scenario_editor(reference_weight: float) -> None:
    st.markdown("**Activități în scenariu**")
    rows = st.session_state.get(WHAT_IF_ACTIVITY_ROWS_KEY, [])
    if not rows:
        st.info("Scenariul nu conține activități.")
        return

    for index, row in enumerate(list(rows)):
        scenario_id = row["scenario_id"]
        with st.container(border=True):
            name_col, calories_col, duration_col, details_col, action_col = st.columns(
                [1.9, 0.85, 0.9, 1.5, 0.75],
                vertical_alignment="center",
            )
            with name_col:
                st.markdown(f"**{row.get('label', '-')}**")
                st.caption(f"{row.get('category', '-')} | {row.get('source_label', 'MacroSense')}")
            with duration_col:
                duration_key = f"what_if_activity_duration_{scenario_id}"
                duration = st.number_input(
                    "Durată (min)",
                    **_number_input_kwargs(
                        duration_key,
                        float(row.get("duration_min") or 30.0),
                        step=5.0,
                        help=duration_range_help(),
                    ),
                )
                duration_error = validate_duration_minutes(duration)
                _render_inline_validation_message(duration_error)
                row["duration_min"] = float(duration)
            with details_col:
                if _is_strength_category(row.get("category")):
                    sets_col, reps_col = st.columns(2)
                    with sets_col:
                        sets_key = f"what_if_activity_sets_{scenario_id}"
                        row["sets"] = st.number_input(
                            "Seturi",
                            **_number_input_kwargs(
                                sets_key,
                                int(row.get("sets") or 3),
                                step=1,
                            ),
                        )
                        sets_error = validate_sets(row["sets"])
                        _render_inline_validation_message(sets_error)
                    with reps_col:
                        reps_key = f"what_if_activity_reps_{scenario_id}"
                        row["reps"] = st.number_input(
                            "Repetări",
                            **_number_input_kwargs(
                                reps_key,
                                int(row.get("reps") or 10),
                                step=1,
                            ),
                        )
                        reps_error = validate_reps(row["reps"])
                        _render_inline_validation_message(reps_error)
                manual_toggle_key = f"what_if_activity_manual_toggle_{scenario_id}"
                use_manual = st.checkbox(
                    "Calorii manuale",
                    **_checkbox_kwargs(
                        manual_toggle_key,
                        row.get("manual_calories_burned") is not None,
                    ),
                )
                if use_manual:
                    manual_value = (
                        row.get("manual_calories_burned")
                        or row.get("last_manual_calories_burned")
                        or row.get("default_manual_calories_burned")
                        or 100.0
                    )
                    manual_key = f"what_if_activity_manual_{scenario_id}"
                    row["manual_calories_burned"] = st.number_input(
                        "Calorii arse",
                        **_number_input_kwargs(
                            manual_key,
                            float(manual_value),
                            step=10.0,
                        ),
                    )
                    row["last_manual_calories_burned"] = row["manual_calories_burned"]
                    manual_error = _validate_manual_calories_ui(row["manual_calories_burned"])
                    _render_inline_validation_message(manual_error)
                else:
                    if row.get("manual_calories_burned") is not None:
                        row["last_manual_calories_burned"] = row["manual_calories_burned"]
                    row["manual_calories_burned"] = None
                    st.session_state.pop(f"what_if_activity_manual_{scenario_id}", None)
            with calories_col:
                _render_scenario_row_calories(
                    _calculate_activity_row_calories(row, reference_weight)
                )
            with action_col:
                if st.button(
                    "Elimină",
                    key=f"what_if_remove_activity_{scenario_id}",
                    type="tertiary",
                    width="stretch",
                ):
                    st.session_state[WHAT_IF_ACTIVITY_ROWS_KEY].pop(index)
                    st.rerun()


def _render_add_activity_section(reference_weight: float) -> None:
    with st.expander("Adaugă activitate doar în scenariu"):
        activity_options = Activity.get_catalog_options()
        if not activity_options:
            st.info("Nu există activități în catalog.")
            return

        search_col, category_col = st.columns([2, 1])
        with search_col:
            search_text = st.text_input(
                "Caută activitate",
                placeholder="Ex: alergare, flotări, bicicletă",
                key=_versioned_widget_key("what_if_activity_search"),
            ).strip()
        with category_col:
            category_filter = st.selectbox(
                "Categorie",
                get_activity_category_filter_options(activity_options),
                key=_versioned_widget_key("what_if_activity_category_filter"),
            )

        selection_df = build_activity_selection_dataframe(
            activity_options,
            search_text,
            category_filter,
        )
        if selection_df.empty:
            st.info("Nu există activități pentru filtrele selectate.")
            return

        selection_state = st.dataframe(
            selection_df,
            width="stretch",
            height=get_table_height(selection_df, max_rows=8),
            hide_index=True,
            column_order=["Denumire", "Categorie", "Sursă", "Metodă MET", "MET"],
            column_config={
                "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
                "Categorie": st.column_config.TextColumn("Categorie", width="small"),
                "Sursă": st.column_config.TextColumn("Sursă", width="small"),
                "Metodă MET": st.column_config.TextColumn("Metodă MET", width="medium"),
                "MET": st.column_config.NumberColumn("MET", format="%.1f", width="small"),
            },
            key=build_activity_selection_state_key(
                search_text,
                category_filter,
                key_prefix=_versioned_widget_key("what_if_activity_selection_table"),
            ),
            on_select="rerun",
            selection_mode="single-row",
            row_height=32,
        )
        selected_rows = selection_state.selection.rows
        selected_activity_id = None
        if selected_rows and selected_rows[0] < len(selection_df):
            selected_activity_id = int(selection_df.iloc[selected_rows[0]]["_activity_id"])

        selected_activity = activity_options.get(selected_activity_id) if selected_activity_id else None
        if selected_activity:
            st.caption(
                f"Sursă MET: {selected_activity.get('source_label', 'MacroSense')} · "
                f"{selected_activity.get('met_method_label', 'Manual Admin')}"
            )
        else:
            st.caption("Selectează o activitate pentru a calcula estimarea calorică.")

        is_strength = _is_strength_category(selected_activity.get("category")) if selected_activity else False
        input_col, detail_col = st.columns(2)
        with input_col:
            duration = st.number_input(
                "Durată TOTALĂ sesiune (minute)",
                value=30.0,
                step=0.1,
                help=(
                    "Timpul total petrecut la acest exercițiu, inclusiv pauzele dintre seturi. "
                    f"{duration_range_help()}"
                ),
                key=_versioned_widget_key("what_if_add_activity_duration"),
            )
        with detail_col:
            if is_strength:
                sets = st.number_input(
                    "Seturi",
                    value=3,
                    step=1,
                    key=_versioned_widget_key("what_if_add_activity_sets"),
                )
                reps = st.number_input(
                    "Repetări pe set",
                    value=12,
                    step=1,
                    key=_versioned_widget_key("what_if_add_activity_reps"),
                )
            else:
                st.info("📌 Seturile și repetările se aplică doar la exerciții de Forță.")
                sets = None
                reps = None

        calc_sets = sets if is_strength else None
        calc_reps = reps if is_strength else None
        duration_error = validate_duration_minutes(duration, "Durata adăugată")
        sets_error = validate_sets(calc_sets) if is_strength else None
        reps_error = validate_reps(calc_reps) if is_strength else None
        estimated_burned = None
        preview_error = None
        if selected_activity and not _get_first_error(duration_error, sets_error, reps_error):
            try:
                preview_entry = build_activity_entry(
                    entry_id="preview",
                    label=selected_activity["name"],
                    category=selected_activity.get("category") or "Altele",
                    duration_min=duration,
                    met=selected_activity["met"],
                    weight_kg=reference_weight,
                    sets=calc_sets,
                    reps=calc_reps,
                    source_label=selected_activity.get("source_label") or "MacroSense",
                    is_existing=False,
                )
                estimated_burned = preview_entry.calories_burned
                st.caption(f"🔥 Calorii estimate consumate: **{estimated_burned:.1f} kcal**")
            except ValueError:
                preview_error = "Activitatea selectată nu poate fi simulată cu valorile introduse."

        use_manual_calories = st.checkbox(
            "Folosesc caloriile raportate de ceas/aparat cardio",
            key=_versioned_widget_key("what_if_add_activity_manual_toggle"),
            help="Valoarea manuală va înlocui estimarea MET/TUT doar în scenariul simulat.",
        )
        manual_calories = None
        manual_calories_error = None
        if use_manual_calories:
            manual_calories = st.number_input(
                "Calorii arse raportate",
                value=float(max(1, round(estimated_burned or 1, 1))),
                step=1.0,
                key=_versioned_widget_key("what_if_add_activity_manual"),
            )
            manual_calories_error = _validate_manual_calories_ui(manual_calories)
            if not manual_calories_error:
                st.caption(f"Se va folosi valoarea manuală: **{manual_calories:.1f} kcal**")

        validation_error = _get_first_error(
            duration_error,
            sets_error,
            reps_error,
            preview_error,
            manual_calories_error,
        )
        if validation_error:
            st.error(validation_error)

        if st.button(
            "Adaugă activitatea în scenariu",
            key="what_if_add_activity_button",
            width="stretch",
            type="primary",
            disabled=selected_activity is None,
        ):
            if validation_error:
                return
            try:
                entry = build_activity_entry(
                    entry_id=_next_scenario_id("activity"),
                    label=selected_activity["name"],
                    category=selected_activity.get("category") or "Altele",
                    duration_min=duration,
                    met=selected_activity["met"],
                    weight_kg=reference_weight,
                    sets=calc_sets,
                    reps=calc_reps,
                    manual_calories_burned=manual_calories if use_manual_calories else None,
                    source_label=selected_activity.get("source_label") or "MacroSense",
                    is_existing=False,
                )
            except ValueError:
                st.error("Activitatea selectată nu poate fi simulată cu valorile introduse.")
                return
            st.session_state[WHAT_IF_ACTIVITY_ROWS_KEY].append(
                {
                    "scenario_id": entry.entry_id,
                    "label": entry.label,
                    "category": entry.category,
                    "duration_min": entry.duration_min,
                    "sets": entry.sets,
                    "reps": entry.reps,
                    "manual_calories_burned": entry.manual_calories_burned,
                    "met": entry.met,
                    "source_label": entry.source_label,
                    "is_existing": False,
                }
            )
            st.rerun()


def _build_entries(
    food_rows: list[dict],
    activity_rows: list[dict],
    reference_weight: float,
) -> tuple[list[WhatIfFoodEntry], list[WhatIfActivityEntry], list[str]]:
    errors = []
    food_entries: list[WhatIfFoodEntry] = []
    activity_entries: list[WhatIfActivityEntry] = []

    for row in food_rows:
        try:
            food_entries.append(
                build_food_entry(
                    entry_id=row["scenario_id"],
                    label=row.get("label"),
                    entry_type=row.get("entry_type"),
                    quantity_g=row.get("quantity_g"),
                    calories_100g=row.get("calories_100g"),
                    protein_100g=row.get("protein_100g"),
                    carbs_100g=row.get("carbs_100g"),
                    fats_100g=row.get("fats_100g"),
                    source_label=row.get("source_label") or "MacroSense",
                    is_existing=row.get("is_existing", False),
                )
        )
        except ValueError:
            errors.append(_format_food_row_error(row))

    for row in activity_rows:
        try:
            activity_entries.append(
                build_activity_entry(
                    entry_id=row["scenario_id"],
                    label=row.get("label"),
                    category=row.get("category"),
                    duration_min=row.get("duration_min"),
                    met=row.get("met"),
                    weight_kg=reference_weight,
                    sets=row.get("sets"),
                    reps=row.get("reps"),
                    manual_calories_burned=row.get("manual_calories_burned"),
                    source_label=row.get("source_label") or "MacroSense",
                    is_existing=row.get("is_existing", False),
                )
            )
        except ValueError:
            errors.append(_format_activity_row_error(row))

    return food_entries, activity_entries, errors


def _format_food_row_error(row: dict) -> str:
    quantity_error = validate_quantity_g(row.get("quantity_g"))
    if quantity_error:
        return f"{row.get('label', 'Aliment')}: {quantity_error}"
    return f"{row.get('label', 'Aliment')}: valorile nutriționale nu pot fi simulate."


def _format_activity_row_error(row: dict) -> str:
    duration_error = validate_duration_minutes(row.get("duration_min"))
    if duration_error:
        return f"{row.get('label', 'Activitate')}: {duration_error}"
    manual_calories = row.get("manual_calories_burned")
    if manual_calories is not None:
        manual_error = _validate_manual_calories_ui(manual_calories)
        if manual_error:
            return f"{row.get('label', 'Activitate')}: {manual_error}"
    return f"{row.get('label', 'Activitate')}: valorile activității nu pot fi simulate."


def _render_comparison(comparison) -> None:
    st.subheader("Rezultat What-if")
    rows = [
        _comparison_row(
            "Calorii consumate",
            comparison.real.calories_in,
            comparison.simulated.calories_in,
            comparison.difference.calories_in,
            "kcal",
            real_unavailable=not comparison.real.has_food_entries,
            simulated_unavailable=not comparison.simulated.has_food_entries,
            difference_unavailable=not (
                comparison.real.has_food_entries and comparison.simulated.has_food_entries
            ),
        ),
        _comparison_row("Proteine", comparison.real.protein_g, comparison.simulated.protein_g, comparison.difference.protein_g, "g"),
        _comparison_row("Carbohidrați", comparison.real.carbs_g, comparison.simulated.carbs_g, comparison.difference.carbs_g, "g"),
        _comparison_row("Grăsimi", comparison.real.fats_g, comparison.simulated.fats_g, comparison.difference.fats_g, "g"),
        _comparison_row("Calorii activități", comparison.real.activity_calories, comparison.simulated.activity_calories, comparison.difference.activity_calories, "kcal"),
        _comparison_row("TDEE estimat", comparison.real.estimated_tdee, comparison.simulated.estimated_tdee, comparison.difference.estimated_tdee, "kcal"),
        _comparison_row("Balanță estimată", comparison.real.estimated_balance, comparison.simulated.estimated_balance, comparison.difference.estimated_balance, "kcal"),
    ]
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Metrică": st.column_config.TextColumn("Metrică", width="medium"),
            "Valori reale": st.column_config.TextColumn("Valori reale", width="small"),
            "Scenariu simulat": st.column_config.TextColumn("Scenariu simulat", width="small"),
            "Diferență": st.column_config.TextColumn("Diferență", width="small"),
        },
    )

    if scenario_matches_real_day(comparison):
        st.success("Scenariul este identic cu ziua reală. Nu există modificări simulate.")
    else:
        st.info(describe_balance_delta(comparison.difference.estimated_balance))
    if comparison.difference.estimated_balance is not None:
        impact_14 = calculate_repeated_daily_weight_impact(comparison.difference.estimated_balance, 14)
        impact_30 = calculate_repeated_daily_weight_impact(comparison.difference.estimated_balance, 30)
        st.caption(
            "Impact teoretic dacă aceeași diferență față de ziua reală s-ar repeta zilnic: "
            f"{impact_14:+.2f} kg în 14 zile și {impact_30:+.2f} kg în 30 zile. "
            "Aceasta este o formulă deterministă, separată de predicția ML."
        )


def _comparison_row(
    label: str,
    real: float | None,
    simulated: float | None,
    difference: float | None,
    suffix: str,
    *,
    real_unavailable: bool = False,
    simulated_unavailable: bool = False,
    difference_unavailable: bool = False,
) -> dict:
    return {
        "Metrică": label,
        "Valori reale": _format_value(real, suffix, unavailable=real_unavailable),
        "Scenariu simulat": _format_value(
            simulated,
            suffix,
            unavailable=simulated_unavailable,
        ),
        "Diferență": _format_signed_value(
            difference,
            suffix,
            unavailable=difference_unavailable,
        ),
    }


def _format_value(value: Any, suffix: str, *, unavailable: bool = False) -> str:
    if unavailable or value is None:
        return UNAVAILABLE_RESULT_VALUE
    if suffix == "kcal":
        return format_kcal_for_display(value)
    return f"{float(value):.1f} {suffix}"


def _format_signed_value(value: Any, suffix: str, *, unavailable: bool = False) -> str:
    if unavailable or value is None:
        return UNAVAILABLE_RESULT_VALUE
    if suffix == "kcal":
        return format_kcal_for_display(value, signed=True)
    return f"{float(value):+.1f} {suffix}"


def _format_source_context(row: dict) -> str:
    meal_type = row.get("meal_type")
    meal_time = format_time_for_display(row.get("meal_time"))
    source = row.get("source_label") or "MacroSense"
    if meal_type and meal_time != "-":
        return f"{row.get('entry_type', 'Aliment')} | {source} | {meal_type}, {meal_time}"
    return f"{row.get('entry_type', 'Aliment')} | {source}"


def _validate_manual_calories_ui(value: Any) -> str | None:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "Caloriile manuale trebuie să fie un număr valid."
    if numeric_value < ActivityLog.MIN_MANUAL_CALORIES_BURNED:
        return (
            "Caloriile manuale trebuie să fie cel puțin "
            f"{ActivityLog.MIN_MANUAL_CALORIES_BURNED:.0f} kcal."
        )
    if numeric_value > ActivityLog.MAX_MANUAL_CALORIES_BURNED:
        return (
            "Caloriile manuale trebuie să fie cel mult "
            f"{ActivityLog.MAX_MANUAL_CALORIES_BURNED:.0f} kcal."
        )
    return None


def _next_scenario_id(prefix: str) -> str:
    st.session_state[WHAT_IF_COUNTER_KEY] = int(st.session_state.get(WHAT_IF_COUNTER_KEY, 0)) + 1
    return f"sim_{prefix}_{st.session_state[WHAT_IF_COUNTER_KEY]}"
