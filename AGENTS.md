# MacroSense — AGENTS.md

## Stack tehnic
- Backend/UI: Python 3.x + Streamlit
- Baza de date: PostgreSQL via psycopg2 (niciodată ORM)
- Structura fișierelor:
  - app.py — entrypoint Streamlit: configurează aplicația și rutează pe roluri
  - assets/style.css — stiluri CSS locale pentru polish UI
  - ui/config.py — configurare Streamlit și încărcare CSS local
  - ui/tables.py — randare tabele și `column_config`-uri comune
  - ui/formatters.py — helper-e de formatare pentru afișare
  - ui/pages/ — paginile Streamlit separate pe flux:
    - auth_page.py — autentificare și creare cont
    - admin_routes.py — rutare meniu Administrator
    - admin_catalog_pages.py — gestiune cataloage Administrator
    - user_routes.py — rutare meniu Utilizator
    - dashboard_page.py — pagina Acasă
    - food_journal_page.py — Jurnal Alimentar
    - activity_journal_page.py — Jurnal Activități
    - custom_meals_page.py — Mese Personalizate
    - user_catalog_pages.py — cataloage vizibile utilizatorului
  - models/tracking.py — fațadă de compatibilitate care re-exportă clasele din pachetul tracking
  - models/tracking_models/ — pachet domeniu Tracking, separat pe clase:
    - food_item.py — FoodItem
    - activity.py — Activity
    - food_log.py — FoodLog
    - activity_log.py — ActivityLog
    - recipe_ingredient.py — RecipeIngredient
    - custom_meal.py — CustomMeal
    - daily_log.py — DailyLog
    - weight_log.py — WeightLog
  - models/authentication.py — User, Admin
  - database.py — get_connection()
  - schema.sql — schema completă a bazei de date
  - tests/ — teste automate `unittest` pentru validări OOP și importuri arhitecturale
  - STATUS.md — starea curentă a proiectului (ce e gata, ce e în progres, backlog)
  - docs/DiagramaClase_UPDATED.png — diagrama UML de clase (actualizată)
  - docs/ERD_UPDATED.png — diagrama ERD a bazei de date (actualizată)
  - docs/LICENTA_faranumev12.docx — lucrarea de licență completă
  - docs/STRUCTURA LUCRĂRII DE LICENŢĂ.docx — structura impusă de profesor

## Reguli stricte
- Tot codul (variabile, clase, metode, comentarii) exclusiv în ENGLEZĂ
- Textul din interfața Streamlit (labels, mesaje, titluri) exclusiv în ROMÂNĂ
- Pattern DB obligatoriu: try/except/finally cu conn.close() în finally
- Nu folosi st.form() în Jurnal Alimentar sau Jurnal Activități
- Folosește st.button() cu key explicit pentru submit
- Niciodată cod parțial sau pseudocod — doar cod funcțional complet
- Testele automate din `tests/` se păstrează în proiect și se extind la fiecare
  funcționalitate importantă; nu se șterg după validare.
- Comandă standard teste: `.\venv\Scripts\python.exe -m unittest discover -s tests -v`
- Commit-urile sunt făcute MANUAL de developer după fiecare modificare
  aprobată; AI-ul nu face niciodată commit sau push automat.
  Excepție: AI-ul poate face commit doar când developerul cere explicit acest lucru.

## Regula de Aur
Verifică mereu conformitatea dintre documentația din docs/
(UML, fluxuri, diagrame) și codul efectiv. Orice discrepanță
arhitecturală trebuie semnalată înainte de a scrie cod.

## Arhitectură OOP
- DailyLog: get_or_create, get_for_date, recalculate_totals, get_food_entries,
  get_activity_entries, calculate_hybrid_calories (static),
  get_latest_weight (static), get_by_id, delete_if_empty,
  calculate_energy_balance
- FoodLog: save(), update(), delete()
- ActivityLog: save(), update(), delete()
- RecipeIngredient: metoda save()
- CustomMeal: save, add_ingredient, create_with_ingredients,
  update_with_ingredients, set_status, archive, restore,
  calculate_total_macros, calculateTotalMacros,
  get_user_meal_options(include_archived=False), get_affected_daily_log_ids,
  get_all_as_dataframe, get_ingredients, get_ingredients_as_dataframe
- WeightLog: save(), update(), delete(), get_user_entries(),
  get_reference_for_user(), get_latest_for_user(),
  get_activity_day_weight_references(), get_changed_reference_ids(),
  recalculate_user_daily_logs()
  (`recalculate_user_daily_logs()` recalculează doar zilele cu antrenamente,
  iar cu snapshot anterior recalculează doar zilele unde referința de greutate
  s-a schimbat efectiv)
- User: register(password, weight), authenticate(password)
- Admin: authenticate(password)
- FoodItem, Activity: save(), get_all_as_dataframe(), get_catalog_options()

## Convenții UI
- Metrici Jurnal Activități: layout 3+2 piramidă
  (rând 1: Calorii Forță, Cardio & Altele, Total Arse)
  (rând 2 centrat [0.5,1,1,0.5]: Calorii Consumate, Balanță)
- hide_index=True pe toate st.dataframe()
- Preview caloric live cu st.caption() înainte de butonul de salvare
- Formulare reactive: st.button() cu key= explicit
- În Jurnal Alimentar și Jurnal Activități, panourile reactive cu multe
  widget-uri pot folosi st.fragment() pentru a limita rerender-ul vizual
  și a evita flicker-ul.
- Vizualizarea unei date în Jurnal Alimentar sau Jurnal Activități nu trebuie
  să creeze rânduri goale în `daily_logs`; `DailyLog.get_or_create()` se
  folosește doar la salvarea primei înregistrări reale.
- Mesajele de succes care urmează după operații cu rerun trebuie păstrate
  în st.session_state și afișate ca st.toast(), fără să mute tabelul.
- Selectbox-urile pentru alimente și mese personalizate folosesc ID intern,
  dar afișează utilizatorului doar denumirea, fără sufixe tehnice de tip #id
- Denumirea unei mese personalizate trebuie să înceapă cu literă;
  nu sunt acceptate denumiri care încep cu cifră sau caracter special
- Greutatea inițială din formularul de creare cont se validează manual
  împotriva intervalului `WeightLog.MIN_WEIGHT_KG` - `WeightLog.MAX_WEIGHT_KG`;
  nu se folosește clamp automat prin `min_value/max_value`.
- CSS-ul custom se păstrează în `assets/style.css`, nu inline în `app.py`;
  folosește doar selectori Streamlit stabili sau tag-uri HTML standard,
  niciodată clase generate de tip `st-emotion-cache-*`

## Baza de date
- PostgreSQL local via pgAdmin 4 (localhost:5432)
- Nu executa comenzi psql direct — generează fișiere .sql pentru rulare manuală
- schema.sql este sursa de adevăr pentru structura DB

## Constrângeri speciale DB
- FoodLog folosește o constrângere XOR: are fie food_id,
  fie custom_meal_id (nu ambele simultan)
- Mesele personalizate nu se șterg fizic din UI; se arhivează prin
  `status = 'Arhivată'` pentru a păstra istoricul din Jurnal Alimentar

## Ce NU este implementat încă
- Modul predicție greutate (ML / regresie)
- Recomandări personalizate de mese
- Recomandări personalizate de antrenamente
- Dashboard cu grafice (Plotly/Altair)
- Simulator What-if (scenarii calorice)
