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

## 🟡 La ce lucrăm acum (Focus curent):
- [ ] Implementarea Jurnalului de Activități (`ActivityLog`) — înregistrarea antrenamentelor, obligativitatea `duration_min` și calculul caloriilor arse prin formula MET integrat în `DailyLog.recalculate_totals()`.

## 🔴 Ce urmează (Backlog):
- [ ] Logica pentru Mese Personalizate (`CustomMeal`) — creare rețete cu ingrediente, `calculateTotalMacros()` conform UML și integrare în `recalculate_totals()`.
- [ ] Modulul de Machine Learning — What-if și predicția greutății.
- [ ] Dashboard și generare grafice pentru progres.