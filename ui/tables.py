import pandas as pd
import streamlit as st

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

food_catalog_table_config = {
    "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
    "Calorii/100g": st.column_config.NumberColumn("Calorii/100g", format="%.1f kcal", width="small"),
    "Proteine (g)": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
    "Carbohidrați (g)": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
    "Grăsimi (g)": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
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
