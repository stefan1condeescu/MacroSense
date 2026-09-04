import streamlit as st
from models.tracking import Activity, FoodItem
from ui.language import translate
from ui.tables import render_activity_catalog_table, render_food_catalog_table


def render_user_food_catalog_page() -> None:
    st.header(f"🍎 {translate('Food catalog')}")
    st.subheader(translate("Nutrition database"))
    df_foods = FoodItem.get_all_as_dataframe()
    if not df_foods.empty:
        render_food_catalog_table(df_foods, key_prefix="user")
    else:
        st.info(
            translate(
                "The catalog is currently empty. The administrator will add data soon."
            )
        )


def render_user_activity_catalog_page() -> None:
    st.header(f"🏃‍♂️ {translate('Physical activity catalog')}")
    st.subheader(translate("Available activities"))
    df_activities = Activity.get_all_as_dataframe()
    if not df_activities.empty:
        render_activity_catalog_table(df_activities, key_prefix="user")
    else:
        st.info(translate("The activity catalog is currently empty."))
