# MacroSense — AGENTS.md

## Stack tehnic
- Backend/UI: Python 3.x + Streamlit
- Baza de date: PostgreSQL via psycopg2 (niciodată ORM)
- Structura fișierelor:
  - app.py — entrypoint Streamlit: configurează aplicația și rutează pe roluri
  - assets/style.css — stiluri CSS locale pentru polish UI
  - ui/config.py — configurare Streamlit și încărcare CSS local
  - ui/catalog_constants.py — categoriile locale MacroSense folosite în
    Admin UI și în testele de seed
  - ui/activity_selection.py — helper-e comune pentru selecție activități cu
    search fără diacritice, filtru categorie și afișare sursă/metodă MET
  - ui/activity_validation.py — validare comună pentru durată, seturi și
    repetări fără clamp automat Streamlit
  - ui/food_selection.py — helper-e comune pentru selecție alimente cu search
    fără diacritice, filtru categorie și afișare sursă
  - ui/quantity_validation.py — validare comună pentru cantități în grame
    fără clamp automat Streamlit
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
  - services/ — integrări externe controlate și analytics:
    - usda_food_data.py — client USDA FoodData Central pentru import alimente
    - analytics/energy.py — formule pure pentru BMI, BMR, TDEE estimat și
      balanță calorică estimată
    - analytics/dashboard_data.py — agregări read-only pentru Dashboard v1,
      fără creare de `daily_logs`
  - models/profile_constants.py — valorile canonice pentru câmpurile de profil
    persistate, inclusiv `USER_GOALS`
  - models/text_validation.py — helper-e comune pentru validarea textelor persistente
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
  - database/seeds/ — scripturi SQL opționale pentru populare catalog
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
  (`get_food_entries()` și `get_activity_entries()` trebuie apelate cu
  `user_id` din UI, pentru a păstra izolarea între utilizatori chiar dacă un
  `log_id` ajunge accidental într-un context greșit)
- FoodLog: save(), update(), delete()
  (`meal_type` trebuie să fie una dintre valorile UI/DB: `Mic dejun`,
  `Prânz`, `Cină`, `Gustare`; `meal_time` trebuie să fie un `datetime.time`
  valid, nu `None`; `quantity_g` trebuie să rămână în intervalul 1-5000g;
  pentru `custom_meal_id`, `save()` salvează snapshot nutrițional per 100g
  în `food_logs`, iar `update()` păstrează snapshot-ul existent)
- ActivityLog: save(), update(), delete()
  (`sets` și `reps` trebuie validate împreună și la constructor, nu doar la
  update/UI; fie sunt ambele nule, fie respectă intervalele 1-50 seturi și
  1-200 repetări;
  `duration_min` trebuie să rămână în intervalul 0.1-600 minute;
  `manual_calories_burned` este opțional și, când există, înlocuiește formula
  MET/TUT pentru acea înregistrare)
- RecipeIngredient: metoda save()
  (`quantity_g` trebuie să rămână în intervalul 1-5000g, la fel ca în UI și DB)
- CustomMeal: save, add_ingredient, create_with_ingredients,
  update_with_ingredients, set_status, archive, restore,
  calculate_total_macros, calculateTotalMacros,
  get_user_meal_options(include_archived=False), get_affected_daily_log_ids,
  get_all_as_dataframe, get_ingredients, get_ingredients_as_dataframe
  (`update_with_ingredients()` modifică doar rețeta curentă; nu completează
  snapshot-uri istorice și nu recalculează jurnalele deja salvate)
- WeightLog: save(), update(), delete(), get_user_entries(),
  get_reference_for_user(), get_latest_for_user(),
  get_activity_day_weight_references(), get_changed_reference_ids(),
  recalculate_user_daily_logs()
  (`recalculate_user_daily_logs()` recalculează doar zilele cu antrenamente
  calculate prin MET/TUT, ignorând intrările cu `manual_calories_burned`, iar
  cu snapshot anterior recalculează doar zilele unde referința de greutate s-a
  schimbat efectiv)
- User: register(password, weight), authenticate(password)
  (`goal` trebuie să fie una dintre valorile canonice fără diacritice:
  `Slabire`, `Mentinere`, `Crestere`, definite în `models.profile_constants`)
- Admin: authenticate(password)
- FoodItem, Activity: save(), get_all_as_dataframe(), get_catalog_options()
- FoodItem: external_reference_exists()
- FoodItem.get_catalog_options() trebuie să includă și `source_label`, pentru
  ca selecțiile din Jurnal Alimentar și Mese Personalizate să distingă
  alimentele MacroSense de cele USDA.
- Activity validează la nivel de model denumirea nenulă, categoria nenulă și
  coeficientul MET minim `Activity.MIN_MET_MULTIPLIER`; UI-ul Admin trebuie
  să afișeze erori înainte de salvare pentru aceste cazuri.
- Activity acceptă metadate opționale de sursă pentru catalog:
  `source`, `source_type`, `external_id`, `source_url`, `met_source_code`,
  `met_source_description`, `met_estimation_method`. Metodele permise sunt
  `official_compendium`, `compendium_mapping` și `manual_admin`; activitățile
  oficiale Compendium și mapările MacroSense trebuie diferențiate clar în UI
  și în seed-uri.
- FoodItem validează la nivel de model denumirea nenulă, categoria nenulă,
  valorile nutriționale nenegative, calorii strict pozitive și existența a cel
  puțin unui macronutrient pozitiv; denumirea nu poate conține caractere HTML
  evidente (`<` sau `>`) și trebuie să conțină cel puțin o literă.
- Activity și User blochează caractere HTML evidente (`<` sau `>`) în
  câmpurile text persistente (`name`, `full_name`, `email`); denumirile de
  activități trebuie să conțină cel puțin o literă, iar `full_name` acceptă
  doar litere, spații, cratimă și apostrof.
- FoodItem acceptă metadate opționale de sursă pentru alimente importate:
  `source`, `source_type`, `external_id`, `source_url`;
  importul USDA trebuie să rămână disponibil doar pentru Administrator.
- Email-urile utilizatorilor și administratorilor se curăță prin `strip()`,
  dar nu se convertesc automat la lowercase; autentificarea este sensibilă la
  diferența majuscule/minuscule.

## Convenții UI
- Metrici Jurnal Activități: layout 3+2 piramidă
  (rând 1: Calorii Forță, Cardio & Altele, Total Arse)
  (rând 2 centrat [0.5,1,1,0.5]: Calorii Consumate, Balanță)
- Navigarea principală pentru Utilizator se afișează ca listă radio în sidebar,
  astfel încât `Acasă` și celelalte pagini să rămână vizibile permanent.
- hide_index=True pe toate st.dataframe()
- Listele zilnice din Jurnal Alimentar, Jurnal Activități și Jurnal Greutate se
  afișează ca rânduri/carduri compacte definite prin CSS local, cu toate
  valorile user-entered escapate înainte de HTML custom.
- Preview caloric live cu st.caption() înainte de butonul de salvare
- În Jurnal Activități, utilizatorul poate introduce opțional caloriile
  raportate de ceas/aparat cardio; această valoare se salvează în
  `activity_logs.manual_calories_burned` și înlocuiește estimarea MET/TUT doar
  pentru înregistrarea respectivă.
- Dashboard-ul `Acasă` este read-only și consumă `services.analytics`; nu
  folosește `DailyLog.get_or_create()` și nu creează/modifică date. În
  dashboard, `daily_logs.total_calories_burned` se interpretează ca total
  calorii arse prin activități logate, iar TDEE-ul estimat este derivat prin
  `BMR * 1.2 + activity_calories_burned`.
- Dashboard-ul tratează zilele fără alimente ca zile cu date lipsă, nu ca zile
  cu 0 kcal consumate; balanța calorică estimată se calculează doar pentru zile
  cu alimentație logată.
- Dashboard-ul păstrează metadate pentru greutatea de referință zilnică:
  data sursă, dacă valoarea este imputată, dacă folosește fallback din viitor
  și distanța în zile. Fallback-ul din viitor este permis doar pentru afișare
  read-only în dashboard; dataset-urile ML trebuie să folosească doar referințe
  din trecut pentru a evita data leakage.
- Dashboard-ul raportează separat consistența alimentelor, activităților,
  greutății și consistența generală; aceste valori devin baza pentru feature
  engineering și nu trebuie recombinate implicit în ML fără justificare.
- În Jurnal Activități, alegerea activității din catalog nu folosește selectbox
  pentru liste mari; se face prin căutare, filtru de categorie și tabel
  selectabil, păstrând ID-ul activității doar intern.
- Durata, seturile și repetările din Jurnal Activități se validează manual prin
  `ui.activity_validation`; nu folosi `min_value`/`max_value` pe aceste
  `st.number_input`, ca Streamlit să nu salveze valoarea veche după un warning
  nativ.
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
- În Jurnal Alimentar, alegerea unui aliment din catalog nu mai folosește
  selectbox pentru liste mari; se face prin căutare, filtru de categorie și
  tabel selectabil, păstrând ID-ul alimentului doar intern.
- În Mese Personalizate, alegerea ingredientelor folosește aceeași logică de
  selecție ca Jurnal Alimentar: căutare fără diacritice, filtru categorie,
  tabel selectabil și coloană de sursă.
- Căutările locale de alimente/ingrediente trebuie să fie tolerante la
  diacritice: `capsuni` trebuie să găsească `Căpșuni`.
- Denumirea unei mese personalizate trebuie să înceapă cu literă;
  nu sunt acceptate denumiri care încep cu cifră sau caracter special
- Greutatea inițială din formularul de creare cont se validează manual
  împotriva intervalului `WeightLog.MIN_WEIGHT_KG` - `WeightLog.MAX_WEIGHT_KG`;
  nu se folosește clamp automat prin `min_value/max_value`.
- Cantitățile în grame din Jurnal Alimentar și Mese Personalizate se validează
  manual prin `ui.quantity_validation`; nu folosi `min_value`/`max_value` pe
  `st.number_input`, ca Streamlit să nu salveze valoarea veche după un warning
  nativ.
- Înălțimea și vârsta din formularul de creare cont se validează manual
  împotriva intervalelor `User.MIN_HEIGHT_CM` - `User.MAX_HEIGHT_CM` și
  `User.MIN_AGE` - `User.MAX_AGE`; nu se folosește clamp automat prin
  `min_value/max_value`.
- CSS-ul custom se păstrează în `assets/style.css`, nu inline în `app.py`;
  folosește doar selectori Streamlit stabili sau tag-uri HTML standard,
  niciodată clase generate de tip `st-emotion-cache-*`
- Orice text introdus de utilizator și afișat prin HTML custom cu
  `unsafe_allow_html=True` trebuie escap-at înainte de interpolare.
- Denumirile introduse de utilizator nu trebuie să accepte caractere HTML
  evidente (`<` sau `>`) dacă sunt folosite ca titluri/carduri în UI.

## Baza de date
- PostgreSQL local via pgAdmin 4 (localhost:5432)
- Nu executa comenzi psql direct — generează fișiere .sql pentru rulare manuală
- schema.sql este sursa de adevăr pentru structura DB
- `database/seeds/seed_food_items_usda_starter.sql` este seed opțional pentru
  catalog alimentar extins, cu alimente reale USDA, rulat manual după
  `schema.sql` în pgAdmin.
- `database/seeds/seed_activities_compendium_official.sql` este seed opțional
  pentru activități MET oficiale din 2024 Adult Compendium of Physical
  Activities.
- `database/seeds/seed_activities_macrosense_mappings.sql` este seed opțional
  pentru exerciții practice MacroSense mapate explicit pe coduri generale
  Compendium; aceste exerciții nu trebuie prezentate ca rânduri oficiale
  granulate din Compendium.
- Seed-urile pentru activități se rulează manual după `schema.sql`: mai întâi
  `seed_activities_compendium_official.sql`, apoi
  `seed_activities_macrosense_mappings.sql`.
- `database/seeds/seed_demo_users.sql` este seed opțional pentru utilizatori
  demo sintetici, cu istoric de greutate, jurnale alimentare, jurnale de
  activități și mese personalizate. Se rulează ultimul, după seed-urile de
  alimente și activități.
  Obiectivele demo trebuie să folosească strict valorile canonice
  `Slabire`, `Mentinere`, `Crestere`.
- Importul USDA folosește cheia `FDC_API_KEY` din `.streamlit/secrets.toml`
  sau din variabilele de mediu; cheia nu se comite niciodată în Git.
- Pentru importul de alimente sunt permise inițial doar sursele USDA
  `SR Legacy`, `Foundation` și `Survey (FNDDS)`; `Branded` rămâne exclus
  pentru a evita duplicatele comerciale.
- Alimentele adăugate manual din Admin sunt afișate în UI cu sursa
  `MacroSense`; în DB pot avea `source = NULL`.
- Adăugarea manuală de alimente din Admin trebuie să blocheze denumirea goală,
  denumirile cu caractere HTML evidente (`<`, `>`) și cazul în care toate
  macronutrientele sunt 0 sau caloriile sunt 0.
- Câmpurile nutriționale din formularul Admin pentru alimente se validează
  manual; nu folosi `min_value`/clamp automat care ar putea transforma valori
  invalide negative în 0 înainte de validare. Pentru lizibilitate, formularul
  afișează doar prima eroare de validare la un moment dat.
- Categoriile alimentare sunt categorii locale MacroSense, nu categoriile brute
  USDA; la importul USDA aplicația poate sugera automat categoria, iar Adminul
  o poate ajusta înainte de salvare.
- Categoriile locale de alimente și activități se definesc în
  `ui.catalog_constants`; seed-urile trebuie verificate prin teste să nu
  introducă categorii care nu există în UI.
- Căutarea USDA din Admin trebuie explicată ca fiind în engleză și trebuie să
  filtreze rezultatele irelevante prin potrivirea termenilor căutați în
  descrierea USDA, pentru a evita rezultate de tip `cream of potato` la
  căutarea `ice cream`.

## Constrângeri speciale DB
- FoodLog folosește o constrângere XOR: are fie food_id,
  fie custom_meal_id (nu ambele simultan)
- Mesele personalizate nu se șterg fizic din UI; se arhivează prin
  `status = 'Arhivată'` pentru a păstra istoricul din Jurnal Alimentar
- Mesele personalizate salvate în Jurnal Alimentar păstrează snapshot
  nutrițional per înregistrare în `food_logs`, astfel încât editarea unei
  rețete afectează doar folosirile viitoare, nu istoricul deja logat.
- Pentru intrările cu `custom_meal_id`, snapshot-ul nutrițional este
  obligatoriu la nivel de DB; aplicația nu menține fluxuri de compatibilitate
  pentru intrări incomplete fără snapshot.
- `schema.sql` trebuie să păstreze constrângeri explicite pentru intervale și
  integritate de bază: email normalizat, valori nutriționale nenegative,
  calorii pozitive și cel puțin un macronutrient pozitiv pentru alimente,
  categorie aliment nenulă, denumiri de catalog cu cel puțin o literă, blocare
  caractere HTML evidente în câmpurile text persistente, nume complet fără
  caractere speciale arbitrare, obiectiv utilizator în lista
  `Slabire`/`Mentinere`/`Crestere`, greutate 30-300 kg, MET minim 0.9,
  durată antrenament pozitivă în intervalul 0.1-600 minute, pereche validă
  `sets`/`reps` cu 1-50 seturi și 1-200 repetări, calorii manuale antrenament
  1-5000 kcal când sunt completate, cantități alimentare/ingrediente 1-5000g,
  plus tip/oră de masă obligatorii pentru înregistrările alimentare.

## Ce NU este implementat încă
- Modul predicție greutate (ML / regresie)
- Recomandări personalizate de mese
- Recomandări personalizate de antrenamente
- Dashboard v2 cu predicții/recomandări ML integrate
- Simulator What-if (scenarii calorice)
