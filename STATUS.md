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

## 🟡 La ce lucrăm acum (Focus curent):
- [ ] Polish UI Jurnal Alimentar — ajustări vizuale și de UX rămase.
- [ ] Polish UI Jurnal Activități — ajustări vizuale și de UX rămase.
- [ ] Logica pentru Mese Personalizate (`CustomMeal`) — creare rețete cu ingrediente, implementarea funcției `calculateTotalMacros()` conform diagramei UML și integrarea în calculele zilnice.

## 🔴 Ce urmează (Backlog):
- [ ] Modulul de Machine Learning — What-if și predicția greutății.
- [ ] Dashboard și generare grafice pentru progres.