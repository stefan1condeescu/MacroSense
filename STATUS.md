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
- [x] Implementarea Jurnalului Alimentar (Preluarea datelor din catalog și adăugarea lor pe zile - clasa `DailyLog`), optimizarea stocării `user_id` în sesiune și rezolvarea avertismentelor UI/UX.

## 🟡 La ce lucrăm acum (Focus curent):
- [ ] Implementarea Jurnalului de Activități (`ActivityLog`) - înregistrarea antrenamentelor, obligativitatea duratei și calculul corect al caloriilor arse (MET) integrat în balanța energetică.

## 🔴 Ce urmează (Backlog):
- [ ] Logica pentru Mese Personalizate (CustomMeals) - crearea rețetelor cu ingrediente și calculul macronutrienților.
- [ ] Modulul de Machine Learning (What-if și predicția greutății).
- [ ] Dashboard și generare grafice pentru progres.