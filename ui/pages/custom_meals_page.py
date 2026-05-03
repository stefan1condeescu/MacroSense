import html
import pandas as pd
import streamlit as st
from models.tracking import CustomMeal, DailyLog, FoodItem
from ui.food_selection import build_food_selection_dataframe, build_food_selection_state_key, get_food_category_filter_options
from ui.quantity_validation import quantity_range_help, validate_quantity_g
from ui.tables import get_table_height


def escape_html_text(value) -> str:
    """Escapes user-controlled text before inserting it into custom HTML blocks."""
    return html.escape(str(value))


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
                "custom_meal_ingredient_search_",
                "custom_meal_ingredient_category_",
                "custom_meal_ingredient_table_",
                "custom_meal_edit_ingredient_search_",
                "custom_meal_edit_ingredient_category_",
                "custom_meal_edit_ingredient_table_",
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
        "Sursă": st.column_config.TextColumn("Sursă", width="small"),
        "Cantitate (g)": st.column_config.NumberColumn("Cantitate", format="%.1f g", width="small"),
        "Calorii": st.column_config.NumberColumn("Calorii", format="%.1f kcal", width="small"),
        "Proteine (g)": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
        "Carbohidrați (g)": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
        "Grăsimi (g)": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
    }

    food_selection_table_config = {
        "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
        "Categorie": st.column_config.TextColumn("Categorie", width="small"),
        "Sursă": st.column_config.TextColumn("Sursă", width="small"),
        "Kcal/100g": st.column_config.NumberColumn("Kcal/100g", format="%.1f kcal", width="small"),
        "Proteine": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
        "Carbohidrați": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
        "Grăsimi": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
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

    def render_food_picker(search_key: str, category_key: str, table_key_prefix: str, caption: str):
        filter_col, category_col = st.columns([2, 1])
        with filter_col:
            search_text = st.text_input(
                "Caută ingredient",
                placeholder="Ex: banane, broccoli, capsuni",
                key=search_key
            )
        with category_col:
            category_filter = st.selectbox(
                "Categorie",
                get_food_category_filter_options(food_options),
                key=category_key
            )

        food_selection_df = build_food_selection_dataframe(
            food_options,
            search_text,
            category_filter
        )
        if food_selection_df.empty:
            st.info("Nu există ingrediente pentru căutarea și categoria selectate.")
            return None

        st.caption(caption)
        food_selection_state = st.dataframe(
            food_selection_df,
            width="stretch",
            height=get_table_height(food_selection_df, max_rows=6),
            hide_index=True,
            column_order=["Denumire", "Categorie", "Sursă", "Kcal/100g", "Proteine", "Carbohidrați", "Grăsimi"],
            column_config=food_selection_table_config,
            key=build_food_selection_state_key(search_text, category_filter, table_key_prefix),
            on_select="rerun",
            selection_mode="single-row",
            row_height=32
        )
        selected_rows = food_selection_state.selection.rows
        if selected_rows and selected_rows[0] < len(food_selection_df):
            return int(food_selection_df.iloc[selected_rows[0]]["_food_id"])
        return None
    
    def render_custom_meal_cards(meal_options):
        for meal in meal_options.values():
            is_archived = meal["status"] == CustomMeal.ARCHIVED_STATUS
            card_class = "custom-meal-card archived" if is_archived else "custom-meal-card active"
            status_class = "status-badge archived" if is_archived else "status-badge active"
            safe_recipe_name = escape_html_text(meal["recipe_name"])
            safe_status = escape_html_text(meal["status"])
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="custom-meal-card-header">
                        <strong>{safe_recipe_name}</strong>
                        <span class="{status_class}">{safe_status}</span>
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
        custom_meal_widget_version = st.session_state["custom_meal_widget_version"]
        selected_ingredient_id = render_food_picker(
            search_key=f"custom_meal_ingredient_search_{custom_meal_widget_version}",
            category_key=f"custom_meal_ingredient_category_{custom_meal_widget_version}",
            table_key_prefix=f"custom_meal_ingredient_table_{custom_meal_widget_version}",
            caption="Selectează ingredientul din tabel. Coloana Sursă ajută la diferențierea alimentelor duplicate."
        )
        ingredient_quantity = st.number_input(
            "Cantitate ingredient (g)",
            value=100.0,
            step=1.0,
            key="custom_meal_ingredient_quantity",
            help=quantity_range_help()
        )
    
        selected_ingredient = food_options.get(selected_ingredient_id) if selected_ingredient_id else None
        ingredient_quantity_error = validate_quantity_g(ingredient_quantity, "Cantitatea ingredientului")
        if selected_ingredient:
            if ingredient_quantity_error:
                st.error(ingredient_quantity_error)
            else:
                ingredient_calories = round(selected_ingredient["calories_100g"] * float(ingredient_quantity) / 100.0, 2)
                st.caption(
                    f"🔥 Ingredient selectat: **{selected_ingredient['name']}** "
                    f"({selected_ingredient.get('source_label', 'MacroSense')}) · "
                    f"Calorii estimate: **{ingredient_calories} kcal**"
                )
        else:
            st.caption("Selectează un ingredient pentru a calcula estimarea calorică.")
    
        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button(
                "Adaugă ingredient",
                width="stretch",
                key="btn_add_custom_meal_ingredient",
                type="primary",
                disabled=selected_ingredient is None or bool(ingredient_quantity_error)
            ):
                st.session_state["custom_meal_ingredients"].append({
                    "food_id": selected_ingredient["id"],
                    "name": selected_ingredient["name"],
                    "source_label": selected_ingredient.get("source_label", "MacroSense"),
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
                ingredient.get("source_label", "MacroSense"),
                round(quantity_g, 2),
                round(calories, 2),
                round(protein, 2),
                round(carbs, 2),
                round(fats, 2),
            ])
    
        df_pending = pd.DataFrame(
            rows,
            columns=["Ingredient", "Sursă", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
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
                st.warning("Denumirea mesei trebuie să înceapă cu o literă și nu poate conține caractere de tip HTML.")
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
            selected_edit_ingredient_id = render_food_picker(
                search_key=f"custom_meal_edit_ingredient_search_{selected_edit_meal_id}_{custom_meal_widget_version}",
                category_key=f"custom_meal_edit_ingredient_category_{selected_edit_meal_id}_{custom_meal_widget_version}",
                table_key_prefix=f"custom_meal_edit_ingredient_table_{selected_edit_meal_id}_{custom_meal_widget_version}",
                caption="Selectează ingredientul de adăugat. Pentru liste mari, caută după nume sau filtrează categoria."
            )
            edit_ingredient_quantity = st.number_input(
                "Cantitate ingredient nou (g)",
                value=100.0,
                step=1.0,
                key=f"custom_meal_edit_add_quantity_{selected_edit_meal_id}",
                help=quantity_range_help()
            )
            edit_ingredient_quantity_error = validate_quantity_g(
                edit_ingredient_quantity,
                "Cantitatea ingredientului nou"
            )
            if selected_edit_ingredient_id is not None and edit_ingredient_quantity_error:
                st.error(edit_ingredient_quantity_error)

            if st.button(
                "Adaugă ingredient în rețetă",
                width="stretch",
                key="btn_add_custom_meal_edit_ingredient",
                type="primary",
                disabled=selected_edit_ingredient_id is None or bool(edit_ingredient_quantity_error)
            ):
                selected_edit_ingredient = food_options[selected_edit_ingredient_id]
                st.session_state["custom_meal_edit_row_counter"] += 1
                edit_ingredients.append({
                    "ingredient_id": None,
                    "row_key": f"new_{st.session_state['custom_meal_edit_row_counter']}",
                    "food_id": selected_edit_ingredient["id"],
                    "name": selected_edit_ingredient["name"],
                    "source_label": selected_edit_ingredient.get("source_label", "MacroSense"),
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
            edit_quantity_errors = []
            for ingredient_index, ingredient in enumerate(list(edit_ingredients)):
                row_key = ingredient["row_key"]
                with st.container(border=True):
                    col_name, col_quantity, col_remove = st.columns([2.2, 1, 0.75], vertical_alignment="center")
                    with col_name:
                        st.markdown(f"**{ingredient['name']}**")
                    with col_quantity:
                        updated_quantity = st.number_input(
                            "Cantitate (g)",
                            value=float(ingredient["quantity_g"]),
                            step=1.0,
                            key=f"custom_meal_edit_qty_{selected_edit_meal_id}_{row_key}",
                            label_visibility="collapsed",
                            help=quantity_range_help()
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

                quantity_error = validate_quantity_g(updated_quantity, f"Cantitatea pentru {ingredient['name']}")
                if quantity_error:
                    edit_quantity_errors.append(quantity_error)
                else:
                    edit_ingredients[ingredient_index]["quantity_g"] = float(updated_quantity)

            edit_rows = []
            edit_total_quantity = 0.0
            edit_total_calories = 0.0
            edit_total_protein = 0.0
            edit_total_carbs = 0.0
            edit_total_fats = 0.0

            if edit_quantity_errors:
                st.error(edit_quantity_errors[0])
            else:
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
                        ingredient.get("source_label", "MacroSense"),
                        round(quantity_g, 2),
                        round(calories, 2),
                        round(protein, 2),
                        round(carbs, 2),
                        round(fats, 2),
                    ])

                df_edit = pd.DataFrame(
                    edit_rows,
                    columns=["Ingredient", "Sursă", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
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
        else:
            edit_quantity_errors = []
    
        if st.button(
            "Salvează modificările mesei",
            width="stretch",
            key="btn_update_custom_meal",
            type="primary",
            disabled=bool(edit_quantity_errors)
        ):
            if not edited_recipe_name.strip():
                st.warning("Introdu o denumire pentru masa personalizată.")
            elif not CustomMeal.is_valid_recipe_name(edited_recipe_name):
                st.warning("Denumirea mesei trebuie să înceapă cu o literă și nu poate conține caractere de tip HTML.")
            elif not edit_ingredients:
                st.warning("Masa personalizată trebuie să conțină cel puțin un ingredient.")
            else:
                for ingredient in edit_ingredients:
                    quantity_error = validate_quantity_g(
                        ingredient["quantity_g"],
                        f"Cantitatea pentru {ingredient['name']}"
                    )
                    if quantity_error:
                        st.error(quantity_error)
                        return

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
