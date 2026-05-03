import pandas as pd
import streamlit as st
from ui.food_selection import normalize_search_text


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
    "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
    "Coeficient MET": st.column_config.NumberColumn("MET", format="%.1f", width="small"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
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
    "Durată (min)": st.column_config.NumberColumn("Durată", format="%d min", width="small"),
    "Seturi": st.column_config.TextColumn("Seturi", width="small"),
    "Repetări": st.column_config.TextColumn("Repetări", width="small"),
    "Calorii Arse": st.column_config.NumberColumn("Calorii Arse", format="%.1f kcal", width="small"),
}

weight_log_table_config = {
    "Data": st.column_config.DateColumn("Data", format="DD.MM.YYYY", width="medium"),
    "Greutate (kg)": st.column_config.NumberColumn("Greutate", format="%.1f kg", width="medium"),
}
