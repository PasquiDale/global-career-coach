Agisci come un Senior Python Engineer. Riscrivi COMPLETAMENTE il file `app.py` da zero.
Il codice deve essere MONOLITICO (tutto in un unico file).

OBIETTIVO CRITICO (DESIGN CV):
1. SPAZIATURA INTELLIGENTE:
   - Per "Esperienza" e "Formazione": MANTIENI la riga vuota di stacco tra un elemento e l'altro.
   - Per "Skills", "Lingue" e "Interessi": RIMUOVI la riga vuota tra gli elementi. Devono essere liste compatte.
2. AGGIUNTA SEZIONI: Supporto esplicito per 'languages' e 'interests' nel JSON e nel Word.
3. CONGELATO: Tutto il resto (Header Blu, Foto a Sx, Lettera, Sidebar).

--- ISTRUZIONI RIGIDE CODICE ---

1. IMPORTS:
   `streamlit`, `google.generativeai`, `docx`, `PIL`, `io`, `datetime`.
   `docx.shared`, `docx.enum.table`, `docx.enum.text`.
   `docx.oxml.ns`, `docx.oxml`.

2. CONFIGURAZIONE:
   `st.set_page_config(page_title="Global Career Coach", layout="wide", initial_sidebar_state="expanded")`

3. STATE INIT: Invariato.

4. COSTANTI:

   A) LANG_DISPLAY (Invariato).
   
   B) TRANSLATIONS (Invariato).

   C) SECTION_TITLES (AGGIORNATO CON LINGUE/INTERESSI):
   SECTION_TITLES = {
       'it': {'experience': 'ESPERIENZA PROFESSIONALE', 'education': 'ISTRUZIONE', 'skills': 'COMPETENZE', 'languages': 'LINGUE', 'interests': 'INTERESSI', 'personal_info': 'DATI PERSONALI', 'profile_summary': 'PROFILO'},
       'de_ch': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHEN', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
       'de_de': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHEN', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
       'en_us': {'experience': 'PROFESSIONAL EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFILE'},
       'en_uk': {'experience': 'WORK EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFILE'},
       'fr': {'experience': 'EXPÉRIENCE', 'education': 'FORMATION', 'skills': 'COMPÉTENCES', 'languages': 'LANGUES', 'interests': 'INTÉRÊTS', 'personal_info': 'INFOS', 'profile_summary': 'PROFIL'},
       'es': {'experience': 'EXPERIENCIA', 'education': 'EDUCACIÓN', 'skills': 'HABILIDADES', 'languages': 'IDIOMAS', 'interests': 'INTERESES', 'personal_info': 'DATOS', 'profile_summary': 'PERFIL'},
       'pt': {'experience': 'EXPERIÊNCIA', 'education': 'EDUCAÇÃO', 'skills': 'COMPETÊNCIAS', 'languages': 'IDIOMAS', 'interests': 'INTERESSES', 'personal_info': 'DADOS', 'profile_summary': 'PERFIL'}
   }

5. FUNZIONI HELPER (INVARIATE):
   - `set_table_background`, `add_bottom_border`, `process_image`, `get_todays_date`.

6. FUNZIONE `create_cv_docx` (LOGICA SPAZIATURA CONDIZIONALE):
   - Header Blu/Foto Sx (CONGELATO).
   - Body:
     - Profilo.
     - Definisci ordine sezioni: `['experience', 'education', 'skills', 'languages', 'interests']`.
     - Loop sezioni:
       - Stampa Titolo.
       - Loop elementi lista.
       - Stampa elemento (Bullet).
       - **CONDIZIONE SPAZIO:**
         `if key in ['experience', 'education']:`
             `doc.add_paragraph("")`  # Aggiungi spazio solo per queste.
         `else:`
             `pass`  # Niente spazio per skills, lingue, interessi.

7. FUNZIONE `create_letter_docx` (CONGELATA).

8. LOGICA AI:
   - `models/gemini-3-pro-preview` (No Tools).
   - Prompt Aggiornato: "Output JSON strictly in {selected_language}. Keys: personal_info, cv_sections (must include: profile_summary, experience, education, skills, languages, interests), letter_data."

9. MAIN LOOP:
   - Sidebar fissa.
   - Generazione.

Genera il codice `app.py` completo.
