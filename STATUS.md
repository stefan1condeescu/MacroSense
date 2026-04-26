# Status Proiect - MacroSense

## 🟢 Ce am terminat:
- [x] Setare mediu virtual (venv) și instalare Streamlit.
- [x] Redactare completă a Capitolelor 1, 2 și 3 din licență (în limba română).
- [x] Diagramele UML și ERD finalizate și actualizate cu denumiri în engleză.
- [x] Crearea bazei de date `macrosense_db` în PostgreSQL.
- [x] Rularea scriptului final `schema.sql` în pgAdmin.
- [x] Refactorizare OOP: Crearea arhitecturii de foldere (`/models`).
- [x] Implementarea pachetului de Autentificare (`UserAccount`, `User`, `Admin`).
- [x] Conectarea interfeței Streamlit `app.py` la modelele OOP.
- [x] Implementarea claselor `FoodItem` și `Activity` în pachetul Tracking, respectând Diagrama de Clase OOP.
- [x] Construirea interfeței pentru cataloage (adăugare și vizualizare date).
- [x] Refactorizare Autentificare (UI + OOP): Formular de login unificat cu rutare inteligentă bazată pe roluri, rezolvarea instanțierilor abstracte și restricționarea drepturilor de editare strict pentru Administrator.
- [x] Sincronizare Arhitectură-Documentație: Adăugare `quantity_g` în clasa și tabela `FoodLog` și impunerea duratei obligatorii (`duration_min`) în `activity_logs` pentru acuratețea formulei MET.
- [x] Implementarea clasei `DailyLog` cu `get_or_create`, `recalculate_totals` (OOP-safe, pregătit pentru CustomMeals) și `get_food_entries`.
- [x] Implementarea clasei `FoodLog` cu validare XOR (`food_id` vs `custom_meal_id`) și persistență `quantity_g`.
- [x] Implementarea paginii „Jurnal Alimentar" în Streamlit cu formular de logare, preview calorii estimate și balanță energetică zilnică.
- [x] Optimizare sesiune: `user_id` stocat în `st.session_state` la autentificare (eliminat roundtrip DB per render).
- [x] Fix UI/UX: localizare luni în română, ascundere ID bază de date din tabel, migrare `use_container_width` → `width='stretch'`.
- [x] Actualizarea fluxului de înregistrare (UI + OOP): Preluarea greutății inițiale a utilizatorului și salvarea atomică în `weight_logs` pentru a suporta corect calculele viitoare bazate pe formula MET. Sincronizare documentație (cap. 3.2).
- [x] Implementarea clasei `ActivityLog` în pachetul Tracking: validare `duration_min > 0` la nivel de obiect (`ValueError`), persistență în `activity_logs` via `save()`.
- [x] Extinderea `DailyLog.recalculate_totals()`: calculează atât caloriile IN (`food_logs`) cât și caloriile BURNED (model hibrid TUT pentru Forță, MET clasic pentru Cardio/Altele), cu fallback la 70kg dacă `weight_logs` e gol.
- [x] Implementarea metodelor `DailyLog.get_activity_entries(log_id)` și `DailyLog.get_latest_weight()` în `tracking.py` pentru interogarea istoricului fizic și calcularea dinamică a caloriilor arse per rând.
- [x] Refactorizare UI Jurnal Activități: `st.selectbox` mutat în afara formularului pentru reactivitate dinamică pe schimbare de categorie; câmpurile Seturi/Repetări afișate exclusiv pentru categoria `Forță` (`min_value=1`) și ascunse complet pentru Cardio/Flexibilitate/Sport de echipă.
- [x] Corectare metrici UI: Jurnal Activități afișează breakdown Calorii Forță (TUT) vs. Calorii Cardio & Altele (MET); Jurnal Alimentar afișează corect Calorii consumate / Calorii arse / Balanță energetică.
- [x] Polish UI/UX (Jurnal Alimentar & Activități): Eliminare `st.form` pentru a permite calculul și afișarea în timp real (live preview) a caloriilor estimate consumate/arse direct la interacțiunea cu datele din formulare. Resetarea câmpurilor post-salvare este menținută curat prin `st.rerun()`.
- [x] Polish UI/UX (Cataloage Admin & User): Ascunderea indexului (ID-ului bazei de date / indexului Pandas) din toate cele 4 tabele de afișare pentru cataloagele de Alimente și Activități, standardizând aspectul vizual curat în toată aplicația.
- [x] Polish UI/UX (Jurnal Activități): Redesign secțiune metrici sub formă de piramidă 3+2 — rând 1: Calorii Forță, Calorii Cardio & Altele, Total Calorii Arse; rând 2 centrat: Calorii Consumate și Balanță energetică.
- [x] Implementarea claselor `RecipeIngredient` și `CustomMeal` în `models/tracking.py`, pe structura deja existentă din `schema.sql` (`custom_meals` și `recipe_ingredients`).
- [x] Implementarea metodei `CustomMeal.calculateTotalMacros()` conform diagramei UML, împreună cu varianta Pythonic `calculate_total_macros()`.
- [x] Implementarea salvării atomice a meselor personalizate cu ingrediente prin `CustomMeal.create_with_ingredients()`.
- [x] Integrarea meselor personalizate în `DailyLog.recalculate_totals()`, astfel încât totalul `total_calories_in` include atât alimente simple, cât și mese personalizate consumate.
- [x] Extinderea `DailyLog.get_food_entries()` pentru afișarea intrărilor mixte din jurnal: `Aliment` și `Masă personalizată`.
- [x] Implementarea paginii Streamlit „Mese Personalizate”: creare rețetă, adăugare ingrediente, preview calorii/macronutrienți, salvare și vizualizare ingrediente.
- [x] Extinderea paginii „Jurnal Alimentar” cu opțiunea de a salva în jurnal fie un aliment din catalog, fie o masă personalizată, respectând constrângerea XOR din `FoodLog`.
- [x] Fix UI/UX: eliminarea sufixelor tehnice de tip `#id` din selectbox-urile pentru alimente și mese personalizate, păstrând ID-ul doar intern pentru selecție robustă.
- [x] Polish UI/UX (Mese Personalizate): metrici de preview reorganizate pe două rânduri — Cantitate/Calorii sus, Proteine/Carbohidrați/Grăsimi jos.
- [x] Validare OOP + UI pentru denumirea meselor personalizate: numele trebuie să înceapă cu literă, nu cu cifră sau caracter special.
- [x] Hardening DB access: `FoodItem.get_all_as_dataframe()` și `Activity.get_all_as_dataframe()` au acum `try/except/finally`, aliniat cu regula proiectului.

## 🟡 La ce lucrăm acum (Focus curent):
- [ ] Stabilizare și testare funcțională pentru fluxul complet Mese Personalizate → Jurnal Alimentar → recalculare totaluri zilnice.

## 🔴 Ce urmează (Backlog):
- [ ] Modulul de Machine Learning — predicția greutății.
- [ ] Recomandări personalizate de mese.
- [ ] Simulator What-if (scenarii calorice).
- [ ] Dashboard și generare grafice pentru progres.
- [ ] Clasă dedicată `WeightLog` cu metoda `save()`.
