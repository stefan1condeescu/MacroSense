import pandas as pd
import streamlit as st
from models.tracking import CustomMeal, DailyLog, FoodItem
from ui.tables import get_table_height


def render_custom_meals_page() -> None:
    st.header("🥗 Mese Personalizate")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
        st.stop()
    
    if "custom_meal_ingredients" not in st.session_state:
        st.session_state["custom_meal_ingredients"] = []
    if "custom_meal_edit_ingredients" not in st.session_state:
        st.session_state["custom_meal_edit_ingredients"] = []
    if "custom_meal_edit_row_counter" not in st.session_state:
        st.session_state["custom_meal_edit_row_counter"] = 0
    if "custom_meal_widget_version" not in st.session_state:
        st.session_state["custom_meal_widget_version"] = 0
    
    custom_meal_message = st.session_state.pop("custom_meal_msg", None)
    if st.session_state.pop("custom_meal_reset_widgets", False):
        st.session_state["custom_meal_widget_version"] += 1
        custom_meal_widget_keys = [
            key for key in st.session_state.keys()
            if key.startswith((
                "custom_meal_details_select_",
                "custom_meal_edit_select_",
                "custom_meal_edit_name_",
                "custom_meal_edit_qty_",
                "custom_meal_edit_add_food_",
                "custom_meal_edit_add_quantity_",
                "custom_meal_archive_select_",
                "custom_meal_restore_select_",
            ))
        ]
        for key in custom_meal_widget_keys:
            del st.session_state[key]
    
    def show_custom_meal_message(message):
        if not message:
            return
    
        message_type, message_text = message
        icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
        st.toast(message_text, icon=icon)
    
    def load_custom_meal_edit_state(meal_id, meal_options):
        ingredients = CustomMeal.get_ingredients(meal_id, user_id)
        for ingredient in ingredients:
            ingredient["row_key"] = f"existing_{ingredient['ingredient_id']}"
    
        st.session_state["custom_meal_edit_loaded_id"] = int(meal_id)
        st.session_state["custom_meal_edit_ingredients"] = ingredients
    
    show_custom_meal_message(custom_meal_message)
    
    food_options = FoodItem.get_catalog_options()
    
    ingredient_table_config = {
        "Ingredient": st.column_config.TextColumn("Ingredient", width="medium"),
        "Cantitate (g)": st.column_config.NumberColumn("Cantitate", format="%.1f g", width="small"),
        "Calorii": st.column_config.NumberColumn("Calorii", format="%.1f kcal", width="small"),
        "Proteine (g)": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
        "Carbohidrați (g)": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
        "Grăsimi (g)": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
    }
    
    def render_ingredient_table(dataframe):
        st.dataframe(
            dataframe,
            width="stretch",
            height=get_table_height(dataframe),
            hide_index=True,
            column_config=ingredient_table_config,
            row_height=32
        )
    
    def render_custom_meal_cards(meal_options):
        for meal in meal_options.values():
            is_archived = meal["status"] == CustomMeal.ARCHIVED_STATUS
            card_class = "custom-meal-card archived" if is_archived else "custom-meal-card active"
            status_class = "status-badge archived" if is_archived else "status-badge active"
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="custom-meal-card-header">
                        <strong>{meal['recipe_name']}</strong>
                        <span class="{status_class}">{meal['status']}</span>
                    </div>
                    <div class="custom-meal-card-grid">
                        <div><span>Cantitate</span><strong>{meal['quantity_g']:.0f} g</strong></div>
                        <div><span>Calorii</span><strong>{meal['calories']:.0f} kcal</strong></div>
                        <div><span>Proteine</span><strong>{meal['protein_g']:.1f} g</strong></div>
                        <div><span>Carbohidrați</span><strong>{meal['carbs_g']:.1f} g</strong></div>
                        <div><span>Grăsimi</span><strong>{meal['fats_g']:.1f} g</strong></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.subheader("➕ Creează o masă personalizată")
    recipe_name = st.text_input("Denumire masă", key="custom_meal_name")
    
    if not food_options:
        st.warning("Catalogul de alimente este gol. Administratorul trebuie să adauge alimente mai întâi.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            selected_ingredient_id = st.selectbox(
                "Ingredient",
                options=list(food_options.keys()),
                format_func=lambda food_id: food_options[food_id]["name"],
                key="custom_meal_ingredient_select"
            )
        with col2:
            ingredient_quantity = st.number_input("Cantitate ingredient (g)", min_value=1.0, max_value=5000.0, value=100.0, step=1.0, key="custom_meal_ingredient_quantity")
    
        selected_ingredient = food_options[selected_ingredient_id]
        ingredient_calories = round(selected_ingredient["calories_100g"] * float(ingredient_quantity) / 100.0, 2)
        st.caption(f"🔥 Ingredient selectat: **{ingredient_calories} kcal**")
    
        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button("Adaugă ingredient", width="stretch", key="btn_add_custom_meal_ingredient", type="primary"):
                st.session_state["custom_meal_ingredients"].append({
                    "food_id": selected_ingredient["id"],
                    "name": selected_ingredient["name"],
                    "quantity_g": float(ingredient_quantity),
                    "calories_100g": selected_ingredient["calories_100g"],
                    "protein_g": selected_ingredient["protein_g"],
                    "carbs_g": selected_ingredient["carbs_g"],
                    "fats_g": selected_ingredient["fats_g"],
                })
                st.rerun()
        with col_clear:
            if st.button("Golește lista", width="stretch", key="btn_clear_custom_meal_ingredients", type="tertiary"):
                st.session_state["custom_meal_ingredients"] = []
                st.rerun()
    
    pending_ingredients = st.session_state["custom_meal_ingredients"]
    if pending_ingredients:
        rows = []
        total_quantity = 0.0
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fats = 0.0
    
        for ingredient in pending_ingredients:
            quantity_g = ingredient["quantity_g"]
            calories = ingredient["calories_100g"] * quantity_g / 100.0
            protein = ingredient["protein_g"] * quantity_g / 100.0
            carbs = ingredient["carbs_g"] * quantity_g / 100.0
            fats = ingredient["fats_g"] * quantity_g / 100.0
    
            total_quantity += quantity_g
            total_calories += calories
            total_protein += protein
            total_carbs += carbs
            total_fats += fats
    
            rows.append([
                ingredient["name"],
                round(quantity_g, 2),
                round(calories, 2),
                round(protein, 2),
                round(carbs, 2),
                round(fats, 2),
            ])
    
        df_pending = pd.DataFrame(
            rows,
            columns=["Ingredient", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
        )
        render_ingredient_table(df_pending)
    
        _, col_quantity, col_calories, _ = st.columns([0.85, 1, 1, 0.15])
        col_quantity.metric("Cantitate totală", f"{total_quantity:.0f} g")
        col_calories.metric("Calorii totale", f"{total_calories:.0f} kcal")
    
        st.markdown("<br>", unsafe_allow_html=True)
    
        _, col_protein, col_carbs, col_fats, _ = st.columns([0.75, 1, 1, 1, 0.05])
        col_protein.caption("Proteine")
        col_protein.metric(" ", f"{total_protein:.1f} g", label_visibility="collapsed")
        col_carbs.caption("Carbohidrați")
        col_carbs.metric(" ", f"{total_carbs:.1f} g", label_visibility="collapsed")
        col_fats.caption("Grăsimi")
        col_fats.metric(" ", f"{total_fats:.1f} g", label_visibility="collapsed")
    
        if st.button("Salvează masa personalizată", width="stretch", key="btn_save_custom_meal", type="primary"):
            if not recipe_name.strip():
                st.warning("Introdu o denumire pentru masa personalizată.")
            elif not CustomMeal.is_valid_recipe_name(recipe_name):
                st.warning("Denumirea mesei trebuie să înceapă cu o literă.")
            else:
                saved_meal = CustomMeal.create_with_ingredients(
                    user_id=user_id,
                    recipe_name=recipe_name,
                    ingredients=pending_ingredients
                )
                if saved_meal:
                    st.session_state["custom_meal_ingredients"] = []
                    st.session_state["custom_meal_details_selected_id"] = int(saved_meal.id)
                    st.session_state["custom_meal_edit_selected_id"] = int(saved_meal.id)
                    st.session_state["custom_meal_edit_loaded_id"] = None
                    st.session_state["custom_meal_msg"] = ("success", f"Masa personalizată „{saved_meal.recipe_name}” a fost salvată.")
                    st.session_state["custom_meal_reset_widgets"] = True
                    st.rerun()
                else:
                    st.error("Eroare la salvarea mesei personalizate.")
    else:
        st.info("Adaugă cel puțin un ingredient pentru a salva o masă personalizată.")
    
    st.divider()
    st.subheader("📋 Mesele tale personalizate")
    custom_meal_options = CustomMeal.get_user_meal_options(user_id, include_archived=True)
    if custom_meal_options:
        render_custom_meal_cards(custom_meal_options)
    
        active_meal_options = {
            meal_id: meal
            for meal_id, meal in custom_meal_options.items()
            if meal["status"] == CustomMeal.ACTIVE_STATUS
        }
        archived_meal_options = {
            meal_id: meal
            for meal_id, meal in custom_meal_options.items()
            if meal["status"] == CustomMeal.ARCHIVED_STATUS
        }
        custom_meal_ids = list(custom_meal_options.keys())
        custom_meal_widget_version = st.session_state["custom_meal_widget_version"]
    
        with st.container(border=True):
            st.markdown("#### Arhivă mese personalizate")
            archive_col, restore_col = st.columns(2)
    
            with archive_col:
                st.caption("Scoate o masă activă din lista de folosire viitoare.")
                if active_meal_options:
                    active_meal_ids = list(active_meal_options.keys())
                    selected_archive_meal_id = st.selectbox(
                        "Masă activă",
                        options=active_meal_ids,
                        format_func=lambda meal_id: active_meal_options[meal_id]["recipe_name"],
                        key=f"custom_meal_archive_select_{custom_meal_widget_version}"
                    )
                    if st.button("Arhivează masa", width="stretch", key="btn_archive_custom_meal", type="tertiary"):
                        if CustomMeal.archive(selected_archive_meal_id, user_id):
                            st.session_state["custom_meal_msg"] = (
                                "success",
                                f"Masa „{active_meal_options[selected_archive_meal_id]['recipe_name']}” a fost arhivată."
                            )
                            st.session_state["custom_meal_reset_widgets"] = True
                            st.rerun()
                        else:
                            st.error("Eroare la arhivarea mesei personalizate.")
                else:
                    st.info("Nu ai mese active de arhivat.")
    
            with restore_col:
                st.caption("Readuce o masă arhivată în Jurnal Alimentar.")
                if archived_meal_options:
                    archived_meal_ids = list(archived_meal_options.keys())
                    selected_restore_meal_id = st.selectbox(
                        "Masă arhivată",
                        options=archived_meal_ids,
                        format_func=lambda meal_id: archived_meal_options[meal_id]["recipe_name"],
                        key=f"custom_meal_restore_select_{custom_meal_widget_version}"
                    )
                    if st.button("Reactivează masa", width="stretch", key="btn_restore_custom_meal", type="primary"):
                        if CustomMeal.restore(selected_restore_meal_id, user_id):
                            st.session_state["custom_meal_msg"] = (
                                "success",
                                f"Masa „{archived_meal_options[selected_restore_meal_id]['recipe_name']}” a fost reactivată."
                            )
                            st.session_state["custom_meal_reset_widgets"] = True
                            st.rerun()
                        else:
                            st.error("Eroare la reactivarea mesei personalizate.")
                else:
                    st.info("Nu ai mese arhivate.")
    
        details_select_key = f"custom_meal_details_select_{custom_meal_widget_version}"
        saved_details_meal_id = st.session_state.get("custom_meal_details_selected_id")
        if saved_details_meal_id not in custom_meal_ids:
            st.session_state.pop("custom_meal_details_selected_id", None)
            saved_details_meal_id = None
        details_select_index = custom_meal_ids.index(saved_details_meal_id) if saved_details_meal_id in custom_meal_ids else 0
        st.markdown("#### Vezi ingredientele pentru")
        selected_saved_meal_id = st.selectbox(
            "Alege masa pentru detalii",
            options=custom_meal_ids,
            format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
            index=details_select_index,
            key=details_select_key,
            label_visibility="collapsed"
        )
        st.session_state["custom_meal_details_selected_id"] = int(selected_saved_meal_id)
        selected_saved_meal = custom_meal_options[selected_saved_meal_id]
        df_ingredients = CustomMeal.get_ingredients_as_dataframe(selected_saved_meal["id"], user_id)
        if not df_ingredients.empty:
            render_ingredient_table(df_ingredients)
    
        st.divider()
        st.subheader("✏️ Editează o masă personalizată")
        edit_select_key = f"custom_meal_edit_select_{custom_meal_widget_version}"
        saved_edit_meal_id = st.session_state.get("custom_meal_edit_selected_id")
        if saved_edit_meal_id not in custom_meal_ids:
            st.session_state.pop("custom_meal_edit_selected_id", None)
            saved_edit_meal_id = None
        edit_select_index = custom_meal_ids.index(saved_edit_meal_id) if saved_edit_meal_id in custom_meal_ids else 0
        selected_edit_meal_id = st.selectbox(
            "Masă de editat",
            options=custom_meal_ids,
            format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
            index=edit_select_index,
            key=edit_select_key
        )
        st.session_state["custom_meal_edit_selected_id"] = int(selected_edit_meal_id)
    
        if st.session_state.get("custom_meal_edit_loaded_id") != int(selected_edit_meal_id):
            load_custom_meal_edit_state(selected_edit_meal_id, custom_meal_options)
    
        edit_name_key = f"custom_meal_edit_name_{selected_edit_meal_id}_{custom_meal_widget_version}"
        edited_recipe_name = st.text_input(
            "Denumire nouă masă",
            value=custom_meal_options[selected_edit_meal_id]["recipe_name"],
            key=edit_name_key
        )
        edit_ingredients = st.session_state["custom_meal_edit_ingredients"]
    
        if food_options:
            col_add_food, col_add_quantity = st.columns(2)
            with col_add_food:
                selected_edit_ingredient_id = st.selectbox(
                    "Ingredient de adăugat",
                    options=list(food_options.keys()),
                    format_func=lambda food_id: food_options[food_id]["name"],
                    key=f"custom_meal_edit_add_food_{selected_edit_meal_id}"
                )
            with col_add_quantity:
                edit_ingredient_quantity = st.number_input(
                    "Cantitate ingredient nou (g)",
                    min_value=1.0,
                    max_value=5000.0,
                    value=100.0,
                    step=1.0,
                    key=f"custom_meal_edit_add_quantity_{selected_edit_meal_id}"
                )
    
            if st.button("Adaugă ingredient în rețetă", width="stretch", key="btn_add_custom_meal_edit_ingredient", type="primary"):
                selected_edit_ingredient = food_options[selected_edit_ingredient_id]
                st.session_state["custom_meal_edit_row_counter"] += 1
                edit_ingredients.append({
                    "ingredient_id": None,
                    "row_key": f"new_{st.session_state['custom_meal_edit_row_counter']}",
                    "food_id": selected_edit_ingredient["id"],
                    "name": selected_edit_ingredient["name"],
                    "quantity_g": float(edit_ingredient_quantity),
                    "calories_100g": selected_edit_ingredient["calories_100g"],
                    "protein_g": selected_edit_ingredient["protein_g"],
                    "carbs_g": selected_edit_ingredient["carbs_g"],
                    "fats_g": selected_edit_ingredient["fats_g"],
                })
                st.rerun()
        else:
            st.warning("Catalogul de alimente este gol. Nu poți adăuga ingrediente noi momentan.")
    
        if edit_ingredients:
            st.caption("Ingrediente curente")
            for ingredient_index, ingredient in enumerate(list(edit_ingredients)):
                row_key = ingredient["row_key"]
                with st.container(border=True):
                    col_name, col_quantity, col_remove = st.columns([2.2, 1, 0.75], vertical_alignment="center")
                    with col_name:
                        st.markdown(f"**{ingredient['name']}**")
                    with col_quantity:
                        updated_quantity = st.number_input(
                            "Cantitate (g)",
                            min_value=1.0,
                            max_value=5000.0,
                            value=float(ingredient["quantity_g"]),
                            step=1.0,
                            key=f"custom_meal_edit_qty_{selected_edit_meal_id}_{row_key}",
                            label_visibility="collapsed"
                        )
                    with col_remove:
                        if st.button(
                            "Elimină",
                            key=f"btn_remove_custom_meal_edit_{selected_edit_meal_id}_{row_key}",
                            type="tertiary",
                            width="stretch"
                        ):
                            edit_ingredients.pop(ingredient_index)
                            st.rerun()
    
                edit_ingredients[ingredient_index]["quantity_g"] = float(updated_quantity)
    
            edit_rows = []
            edit_total_quantity = 0.0
            edit_total_calories = 0.0
            edit_total_protein = 0.0
            edit_total_carbs = 0.0
            edit_total_fats = 0.0
    
            for ingredient in edit_ingredients:
                quantity_g = ingredient["quantity_g"]
                calories = ingredient["calories_100g"] * quantity_g / 100.0
                protein = ingredient["protein_g"] * quantity_g / 100.0
                carbs = ingredient["carbs_g"] * quantity_g / 100.0
                fats = ingredient["fats_g"] * quantity_g / 100.0
    
                edit_total_quantity += quantity_g
                edit_total_calories += calories
                edit_total_protein += protein
                edit_total_carbs += carbs
                edit_total_fats += fats
    
                edit_rows.append([
                    ingredient["name"],
                    round(quantity_g, 2),
                    round(calories, 2),
                    round(protein, 2),
                    round(carbs, 2),
                    round(fats, 2),
                ])
    
            df_edit = pd.DataFrame(
                edit_rows,
                columns=["Ingredient", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
            )
            render_ingredient_table(df_edit)
    
            _, col_edit_quantity, col_edit_calories, _ = st.columns([0.85, 1, 1, 0.15])
            col_edit_quantity.metric("Cantitate totală", f"{edit_total_quantity:.0f} g")
            col_edit_calories.metric("Calorii totale", f"{edit_total_calories:.0f} kcal")
    
            st.markdown("<br>", unsafe_allow_html=True)
    
            _, col_edit_protein, col_edit_carbs, col_edit_fats, _ = st.columns([0.75, 1, 1, 1, 0.05])
            col_edit_protein.caption("Proteine")
            col_edit_protein.metric(" ", f"{edit_total_protein:.1f} g", label_visibility="collapsed")
            col_edit_carbs.caption("Carbohidrați")
            col_edit_carbs.metric(" ", f"{edit_total_carbs:.1f} g", label_visibility="collapsed")
            col_edit_fats.caption("Grăsimi")
            col_edit_fats.metric(" ", f"{edit_total_fats:.1f} g", label_visibility="collapsed")
    
        if st.button("Salvează modificările mesei", width="stretch", key="btn_update_custom_meal", type="primary"):
            if not edited_recipe_name.strip():
                st.warning("Introdu o denumire pentru masa personalizată.")
            elif not CustomMeal.is_valid_recipe_name(edited_recipe_name):
                st.warning("Denumirea mesei trebuie să înceapă cu o literă.")
            elif not edit_ingredients:
                st.warning("Masa personalizată trebuie să conțină cel puțin un ingredient.")
            else:
                affected_log_ids = CustomMeal.get_affected_daily_log_ids(selected_edit_meal_id, user_id)
                updated_meal = CustomMeal.update_with_ingredients(
                    meal_id=selected_edit_meal_id,
                    user_id=user_id,
                    recipe_name=edited_recipe_name,
                    ingredients=edit_ingredients
                )
                if updated_meal:
                    recalculated_logs = 0
                    for log_id in affected_log_ids:
                        affected_daily_log = DailyLog.get_by_id(log_id, user_id)
                        if affected_daily_log and affected_daily_log.recalculate_totals():
                            recalculated_logs += 1
    
                    st.session_state["custom_meal_details_selected_id"] = int(selected_edit_meal_id)
                    st.session_state["custom_meal_edit_selected_id"] = int(selected_edit_meal_id)
                    st.session_state["custom_meal_edit_loaded_id"] = None
                    st.session_state["custom_meal_msg"] = (
                        "success",
                        f"Masa personalizată „{edited_recipe_name.strip()}” a fost actualizată. Jurnale recalculate: {recalculated_logs}."
                    )
                    st.session_state["custom_meal_reset_widgets"] = True
                    st.rerun()
                else:
                    st.error("Eroare la actualizarea mesei personalizate.")
    else:
        st.info("Nu ai încă mese personalizate salvate.")
