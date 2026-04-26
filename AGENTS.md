# MacroSense — AGENTS.md

## Stack tehnic
- Backend/UI: Python 3.x + Streamlit
- Baza de date: PostgreSQL via psycopg2 (niciodată ORM)
- Structura fișierelor:
  - app.py — interfața Streamlit (toate paginile)
  - models/tracking.py — DailyLog, FoodLog, ActivityLog, WeightLog, FoodItem, Activity
  - models/authentication.py — User, Admin
  - database.py — get_connection()
  - schema.sql — schema completă a bazei de date
  - STATUS.md — starea curentă a proiectului (ce e gata, ce e în progres, backlog)

## Reguli stricte
- Tot codul (variabile, clase, metode, comentarii) exclusiv în ENGLEZĂ
- Textul din interfața Streamlit (labels, mesaje, titluri) exclusiv în ROMÂNĂ
- Pattern DB obligatoriu: try/except/finally cu conn.close() în finally
- Nu folosi st.form() în Jurnal Alimentar sau Jurnal Activități
- Folosește st.button() cu key explicit pentru submit
- Niciodată cod parțial sau pseudocod — doar cod funcțional complet
- Commit-urile sunt făcute MANUAL de developer după fiecare modificare
  aprobată — AI-ul nu face niciodată commit sau push automat

## Regula de Aur
Verifică mereu conformitatea dintre documentația din docs/
(UML, fluxuri, diagrame) și codul efectiv. Orice discrepanță
arhitecturală trebuie semnalată înainte de a scrie cod.

## Arhitectură OOP
- DailyLog: get_or_create, recalculate_totals, get_food_entries,
  get_activity_entries, calculate_hybrid_calories (static),
  get_latest_weight (static), calculate_energy_balance
- FoodLog, ActivityLog, WeightLog: metoda save()
- User: register(password, weight), authenticate(password)
- Admin: authenticate(password)
- FoodItem, Activity: save(), get_all_as_dataframe()

## Convenții UI
- Metrici Jurnal Activități: layout 3+2 piramidă
  (rând 1: Calorii Forță, Cardio & Altele, Total Arse)
  (rând 2 centrat [0.5,1,1,0.5]: Calorii Consumate, Balanță)
- hide_index=True pe toate st.dataframe()
- Preview caloric live cu st.caption() înainte de butonul de salvare
- Formulare reactive: st.button() cu key= explicit

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
- Mese Personalizate (CustomMeal)