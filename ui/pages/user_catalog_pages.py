import streamlit as st
from models.tracking import Activity, FoodItem
from ui.tables import activity_catalog_table_config, food_catalog_table_config, render_table


def render_user_food_catalog_page() -> None:
    st.header("🍎 Catalog Alimente")
    st.subheader("Baza de date nutrițională")
    df_foods = FoodItem.get_all_as_dataframe()
    if not df_foods.empty:
        render_table(df_foods, column_config=food_catalog_table_config)
    else:
        st.info("Catalogul este gol în acest moment. Administratorul va adăuga date în curând.")


def render_user_activity_catalog_page() -> None:
    st.header("🏃‍♂️ Catalog Activități Fizice")
    st.subheader("Lista activităților disponibile")
    df_activities = Activity.get_all_as_dataframe()
    if not df_activities.empty:
        render_table(df_activities, column_config=activity_catalog_table_config)
    else:
        st.info("Catalogul de activități este gol în acest moment.")
