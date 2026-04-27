import streamlit as st
from models.tracking import Activity, FoodItem
from ui.tables import activity_catalog_table_config, food_catalog_table_config, render_table


def render_admin_food_catalog_page() -> None:
    st.header("🍎 Gestiune Catalog Alimente")
    with st.expander("➕ Adaugă un aliment nou", expanded=True):
        with st.form("add_food_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Denumire aliment")
                category = st.selectbox("Categorie", ["Fructe", "Legume", "Carne", "Lactate", "Cereale", "Dulciuri", "Altele"])
                calories = st.number_input("Calorii (per 100g)", min_value=0.0, step=1.0)
            with col2:
                protein = st.number_input("Proteine (g)", min_value=0.0, step=0.1)
                carbs = st.number_input("Carbohidrați (g)", min_value=0.0, step=0.1)
                fats = st.number_input("Grăsimi (g)", min_value=0.0, step=0.1)
            
            submit_food = st.form_submit_button("Salvează Alimentul", type="primary")
            
            if submit_food:
                new_food = FoodItem(name, calories, protein, carbs, fats, category)
                if new_food.save():
                    st.success(f"Alimentul '{name}' a fost adăugat cu succes!")
                else:
                    st.error("Eroare la adăugarea alimentului.")
    
    st.subheader("Baza de date nutrițională")
    df_foods = FoodItem.get_all_as_dataframe()
    if not df_foods.empty:
        render_table(df_foods, column_config=food_catalog_table_config)
    else:
        st.info("Catalogul este gol.")


def render_admin_activity_catalog_page() -> None:
    st.header("🏃‍♂️ Gestiune Catalog Activități")
    with st.expander("➕ Adaugă o activitate nouă", expanded=True):
        with st.form("add_activity_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Denumire activitate")
                category = st.selectbox("Categorie", ["Cardio", "Forță", "Flexibilitate", "Sport de echipă"])
            with col2:
                met = st.number_input("Coeficient MET", min_value=0.9, step=0.1, help="Ex: Alergat = 8.0")
            
            submit_act = st.form_submit_button("Salvează Activitatea", type="primary")
            
            if submit_act:
                new_activity = Activity(name, met, category)
                if new_activity.save():
                    st.success(f"Activitatea '{name}' a fost adăugată cu succes!")
                else:
                    st.error("Eroare la adăugarea activității.")
    
    st.subheader("Lista activităților disponibile")
    df_activities = Activity.get_all_as_dataframe()
    if not df_activities.empty:
        render_table(df_activities, column_config=activity_catalog_table_config)
    else:
        st.info("Catalogul de activități este gol.")
