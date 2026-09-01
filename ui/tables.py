import datetime
import html

import pandas as pd
import streamlit as st
from ui.food_selection import (
    format_food_entry_type,
    format_meal_type,
    normalize_search_text,
)
from ui.language import translate


def get_table_height(dataframe: pd.DataFrame, max_rows: int = 6, row_height: int = 32) -> int:
    """Returns a compact dynamic height for Streamlit dataframes."""
    visible_rows = min(max(len(dataframe), 1), max_rows)
    return 38 + visible_rows * row_height


def render_table(dataframe: pd.DataFrame, column_config: dict = None, column_order: list = None, max_rows: int = 6) -> None:
    """Renders a compact dataframe with consistent project styling."""
    st.dataframe(
        dataframe,
        width="stretch",
        height=get_table_height(dataframe, max_rows=max_rows),
        hide_index=True,
        column_config=column_config,
        column_order=column_order,
        row_height=32
    )


def filter_food_catalog_dataframe(
    dataframe: pd.DataFrame,
    search_text: str,
    selected_category: str,
    selected_source: str
) -> pd.DataFrame:
    """Filters food catalog rows using plain text matching, not regex semantics."""
    filtered = dataframe.copy()
    normalized_search = normalize_search_text(search_text)

    if normalized_search:
        normalized_names = (
            filtered["Denumire"]
            .astype(str)
            .apply(normalize_search_text)
        )
        filtered = filtered[
            normalized_names.str.contains(normalized_search, regex=False, na=False)
        ]
    if selected_category != "Toate":
        filtered = filtered[filtered["Categorie"] == selected_category]
    if selected_source != "Toate":
        filtered = filtered[filtered["Sursă"] == selected_source]

    return filtered


def render_food_catalog_table(dataframe: pd.DataFrame, key_prefix: str, max_rows: int = 12) -> None:
    """Renders the food catalog with lightweight filters and clearer scroll context."""
    total_rows = len(dataframe)
    st.caption(
        f"{total_rows} alimente în catalog. Folosește căutarea sau filtrele pentru liste mari."
    )

    filter_col, category_col, source_col = st.columns([2, 1, 1])
    with filter_col:
        search_text = st.text_input(
            "Caută aliment",
            placeholder="Ex: banane, broccoli, pui",
            key=f"{key_prefix}_food_search"
        ).strip()
    with category_col:
        categories = ["Toate"] + sorted(dataframe["Categorie"].dropna().unique().tolist())
        selected_category = st.selectbox(
            "Categorie",
            categories,
            key=f"{key_prefix}_food_category_filter"
        )
    with source_col:
        sources = ["Toate"] + sorted(dataframe["Sursă"].dropna().unique().tolist())
        selected_source = st.selectbox(
            "Sursă",
            sources,
            key=f"{key_prefix}_food_source_filter"
        )

    filtered = filter_food_catalog_dataframe(
        dataframe,
        search_text,
        selected_category,
        selected_source
    )

    if filtered.empty:
        st.info("Nu există alimente pentru filtrele selectate.")
        return

    render_table(filtered, column_config=food_catalog_table_config, max_rows=max_rows)
    if len(filtered) > max_rows:
        st.caption("Tabel scrollabil: derulează în interiorul tabelului pentru restul alimentelor.")


def filter_activity_catalog_dataframe(
    dataframe: pd.DataFrame,
    search_text: str,
    selected_category: str,
    selected_source: str,
    selected_method: str,
) -> pd.DataFrame:
    """Filters activity catalog rows with the same non-regex search semantics as foods."""
    filtered = dataframe.copy()
    normalized_search = normalize_search_text(search_text)

    if normalized_search:
        normalized_names = (
            filtered["Denumire"]
            .astype(str)
            .apply(normalize_search_text)
        )
        filtered = filtered[
            normalized_names.str.contains(normalized_search, regex=False, na=False)
        ]
    if selected_category != "Toate":
        filtered = filtered[filtered["Categorie"] == selected_category]
    if selected_source != "Toate" and "Sursă" in filtered.columns:
        filtered = filtered[filtered["Sursă"] == selected_source]
    if selected_method != "Toate" and "Metodă MET" in filtered.columns:
        filtered = filtered[filtered["Metodă MET"] == selected_method]

    return filtered


def render_activity_catalog_table(dataframe: pd.DataFrame, key_prefix: str, max_rows: int = 12) -> None:
    """Renders the activity catalog with filters for category, source and MET method."""
    total_rows = len(dataframe)
    st.caption(
        f"{total_rows} activități în catalog. Folosește căutarea sau filtrele pentru liste mari."
    )

    filter_col, category_col, source_col, method_col = st.columns([2, 1, 1, 1])
    with filter_col:
        search_text = st.text_input(
            "Caută activitate",
            placeholder="Ex: alergare, flotări, bicicletă",
            key=f"{key_prefix}_activity_search"
        ).strip()
    with category_col:
        categories = ["Toate"] + sorted(dataframe["Categorie"].dropna().unique().tolist())
        selected_category = st.selectbox(
            "Categorie",
            categories,
            key=f"{key_prefix}_activity_category_filter"
        )
    with source_col:
        sources = ["Toate"] + sorted(dataframe.get("Sursă", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_source = st.selectbox(
            "Sursă",
            sources,
            key=f"{key_prefix}_activity_source_filter"
        )
    with method_col:
        methods = ["Toate"] + sorted(dataframe.get("Metodă MET", pd.Series(dtype=str)).dropna().unique().tolist())
        selected_method = st.selectbox(
            "Metodă MET",
            methods,
            key=f"{key_prefix}_activity_method_filter"
        )

    filtered = filter_activity_catalog_dataframe(
        dataframe,
        search_text,
        selected_category,
        selected_source,
        selected_method
    )

    if filtered.empty:
        st.info("Nu există activități pentru filtrele selectate.")
        return

    render_table(filtered, column_config=activity_catalog_table_config, max_rows=max_rows)
    if len(filtered) > max_rows:
        st.caption("Tabel scrollabil: derulează în interiorul tabelului pentru restul activităților.")


def escape_display_text(value) -> str:
    """Escapes values before placing them inside custom HTML blocks."""
    if value is None:
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass
    return html.escape(str(value), quote=True)


def format_card_number(value, suffix: str, decimals: int = 1) -> str:
    """Formats numeric card values while keeping fallback text safe."""
    try:
        return f"{float(value):.{decimals}f} {suffix}".strip()
    except (TypeError, ValueError):
        text = escape_display_text(value)
        return f"{text} {suffix}".strip() if text != "-" and suffix else text


def format_card_date(value) -> str:
    """Formats date-like values for compact log cards."""
    if isinstance(value, datetime.datetime):
        return value.date().strftime("%d.%m.%Y")
    if isinstance(value, datetime.date):
        return value.strftime("%d.%m.%Y")
    return escape_display_text(value)


def build_log_entry_card_html(
    title,
    badge,
    metrics: list[tuple[str, str]],
    card_type: str,
    badge_type: str = "default",
) -> str:
    """Builds one compact HTML card for journal history entries."""
    grid_class = "five" if len(metrics) >= 5 else "two" if len(metrics) <= 2 else ""
    metrics_html = "".join(
        (
            "<div class=\"log-entry-card-metric\">"
            f"<span>{escape_display_text(label)}</span>"
            f"<strong>{escape_display_text(value)}</strong>"
            "</div>"
        )
        for label, value in metrics
    )
    return (
        f'<div class="log-entry-card {escape_display_text(card_type)}">'
        '<div class="log-entry-card-header">'
        f'<strong>{escape_display_text(title)}</strong>'
        f'<span class="log-entry-badge {escape_display_text(badge_type)}">{escape_display_text(badge)}</span>'
        '</div>'
        f'<div class="log-entry-card-grid {grid_class}">'
        f'{metrics_html}'
        '</div>'
        '</div>'
    )


def get_food_log_card_style(entry_type) -> tuple[str, str]:
    """Returns card and badge classes for food journal entry types."""
    normalized_type = str(entry_type or "").strip()
    if normalized_type == "Masă personalizată":
        return "custom-meal", "custom-meal"
    return "food", "food"


def render_log_entry_card(
    title,
    badge,
    metrics: list[tuple[str, str]],
    card_type: str,
    badge_type: str = "default",
) -> None:
    """Renders one compact HTML card for journal history entries."""
    st.markdown(
        build_log_entry_card_html(title, badge, metrics, card_type, badge_type),
        unsafe_allow_html=True,
    )


def build_food_log_cards_html(dataframe: pd.DataFrame) -> str:
    """Build bilingual food-log cards without mutating stable service values."""
    cards_html = []
    for _, row in dataframe.iterrows():
        raw_entry_type = row.get("Tip", "-")
        card_type, badge_type = get_food_log_card_style(raw_entry_type)
        cards_html.append(
            build_log_entry_card_html(
                title=row.get("Aliment / Masă", "-"),
                badge=format_food_entry_type(raw_entry_type),
                card_type=card_type,
                badge_type=badge_type,
                metrics=[
                (
                    translate("Quantity"),
                    format_card_number(row.get("Cantitate (g)"), "g"),
                ),
                (
                    translate("Calories"),
                    format_card_number(row.get("Calorii"), "kcal"),
                ),
                (translate("Meal"), format_meal_type(row.get("Masă", "-"))),
                (translate("Time"), row.get("Ora", "-")),
                ],
            )
        )
    return f'<div class="log-entry-list">{"".join(cards_html)}</div>'


def render_food_log_cards(dataframe: pd.DataFrame) -> None:
    """Renders food journal entries as compact readable cards."""
    st.markdown(build_food_log_cards_html(dataframe), unsafe_allow_html=True)


def render_activity_log_cards(dataframe: pd.DataFrame) -> None:
    """Renders activity journal entries as compact readable cards."""
    cards_html = []
    for _, row in dataframe.iterrows():
        method = row.get("Metodă calcul", "-")
        method_text = str(method)
        badge_type = "manual" if method_text == "Manual" else "estimated"
        cards_html.append(
            build_log_entry_card_html(
                title=row.get("Activitate", "-"),
                badge=method,
                card_type="activity",
                badge_type=badge_type,
                metrics=[
                ("Categorie", row.get("Categorie", "-")),
                ("Durată", format_card_number(row.get("Durată (min)"), "min")),
                ("Seturi", row.get("Seturi", "-")),
                ("Repetări", row.get("Repetări", "-")),
                ("Calorii", format_card_number(row.get("Calorii Arse"), "kcal")),
                ],
            )
        )
    st.markdown(f'<div class="log-entry-list">{"".join(cards_html)}</div>', unsafe_allow_html=True)


def build_weight_log_cards_html(
    dataframe: pd.DataFrame,
    scroll_threshold: int = 6,
) -> tuple[str, bool]:
    """Builds weight history cards and marks long lists as scrollable."""
    cards_html = []
    for _, row in dataframe.iterrows():
        cards_html.append(
            build_log_entry_card_html(
                title=format_card_date(row.get("Data")),
                badge="Greutate",
                card_type="weight",
                badge_type="weight",
                metrics=[
                ("Greutate", format_card_number(row.get("Greutate (kg)"), "kg")),
                ],
            )
        )
    is_scrollable = len(dataframe) > scroll_threshold
    list_classes = "log-entry-list weight-history-list"
    if is_scrollable:
        list_classes += " is-scrollable"
    return f'<div class="{list_classes}">{"".join(cards_html)}</div>', is_scrollable


def render_weight_log_cards(dataframe: pd.DataFrame) -> None:
    """Renders weight history as compact readable cards."""
    cards_html, is_scrollable = build_weight_log_cards_html(dataframe)
    st.markdown(cards_html, unsafe_allow_html=True)
    if is_scrollable:
        st.caption("Istoricul complet este derulabil pentru a păstra pagina compactă.")


food_catalog_table_config = {
    "Denumire": st.column_config.TextColumn("Denumire", width="large"),
    "Calorii/100g": st.column_config.NumberColumn("Kcal/100g", format="%.1f kcal", width="small"),
    "Proteine (g)": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
    "Carbohidrați (g)": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
    "Grăsimi (g)": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
    "Sursă": st.column_config.TextColumn("Sursă", width="medium"),
}

activity_catalog_table_config = {
    "Denumire": st.column_config.TextColumn("Denumire", width="large"),
    "Coeficient MET": st.column_config.NumberColumn("MET", format="%.1f", width="small"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
    "Sursă": st.column_config.TextColumn("Sursă", width="small"),
    "Metodă MET": st.column_config.TextColumn("Metodă MET", width="medium"),
}

food_log_table_config = {
    "Tip": st.column_config.TextColumn("Tip", width="small"),
    "Aliment / Masă": st.column_config.TextColumn("Aliment / Masă", width="medium"),
    "Cantitate (g)": st.column_config.NumberColumn("Cantitate", format="%.1f g", width="small"),
    "Calorii": st.column_config.NumberColumn("Calorii", format="%.1f kcal", width="small"),
    "Masă": st.column_config.TextColumn("Masă", width="small"),
    "Ora": st.column_config.TextColumn("Ora", width="small"),
}

activity_log_table_config = {
    "Activitate": st.column_config.TextColumn("Activitate", width="medium"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
    "Durată (min)": st.column_config.NumberColumn("Durată", format="%.1f min", width="small"),
    "Seturi": st.column_config.TextColumn("Seturi", width="small"),
    "Repetări": st.column_config.TextColumn("Repetări", width="small"),
    "Metodă calcul": st.column_config.TextColumn("Metodă", width="small"),
    "Calorii Arse": st.column_config.NumberColumn("Calorii Arse", format="%.1f kcal", width="small"),
}

weight_log_table_config = {
    "Data": st.column_config.DateColumn("Data", format="DD.MM.YYYY", width="medium"),
    "Greutate (kg)": st.column_config.NumberColumn("Greutate", format="%.1f kg", width="medium"),
}
