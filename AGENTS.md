# MacroSense — AGENTS.md

## Stack tehnic
- Backend/UI: Python 3.x + Streamlit
- Baza de date: PostgreSQL via psycopg2 (niciodată ORM)
- Structura fișierelor:
  - app.py — interfața Streamlit (toate paginile)
  - models/tracking.py — DailyLog, FoodLog, ActivityLog, FoodItem, Activity, CustomMeal, RecipeIngredient
  - models/authentication.py — User, Admin
  - database.py — get_connection()
  - schema.sql — schema completă a bazei de date
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
- Commit-urile sunt făcute MANUAL de developer după fiecare modificare
  aprobată; AI-ul nu face niciodată commit sau push automat.
  Excepție: AI-ul poate face commit doar când developerul cere explicit acest lucru.

## Regula de Aur
Verifică mereu conformitatea dintre documentația din docs/
(UML, fluxuri, diagrame) și codul efectiv. Orice discrepanță
arhitecturală trebuie semnalată înainte de a scrie cod.

## Arhitectură OOP
- DailyLog: get_or_create, recalculate_totals, get_food_entries,
  get_activity_entries, calculate_hybrid_calories (static),
  get_latest_weight (static), calculate_energy_balance
- FoodLog: save(), update(), delete()
- ActivityLog: save(), update(), delete()
- RecipeIngredient: metoda save()
- CustomMeal: save, add_ingredient, create_with_ingredients,
  calculate_total_macros, calculateTotalMacros, get_user_meal_options,
  get_all_as_dataframe, get_ingredients_as_dataframe
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
- Mesajele de succes care urmează după operații cu rerun trebuie păstrate
  în st.session_state și afișate ca st.toast(), fără să mute tabelul.
- Selectbox-urile pentru alimente și mese personalizate folosesc ID intern,
  dar afișează utilizatorului doar denumirea, fără sufixe tehnice de tip #id
- Denumirea unei mese personalizate trebuie să înceapă cu literă;
  nu sunt acceptate denumiri care încep cu cifră sau caracter special

## Baza de date
- PostgreSQL local via pgAdmin 4 (localhost:5432)
- Nu executa comenzi psql direct — generează fișiere .sql pentru rulare manuală
- schema.sql este sursa de adevăr pentru structura DB

## Constrângeri speciale DB
- FoodLog folosește o constrângere XOR: are fie food_id,
  fie custom_meal_id (nu ambele simultan)

## Ce NU este implementat încă
- Modul predicție greutate (ML / regresie)
- Recomandări personalizate de mese
- Dashboard cu grafice (Plotly/Altair)
- Simulator What-if (scenarii calorice)
- Clasa dedicată WeightLog cu metoda save()
