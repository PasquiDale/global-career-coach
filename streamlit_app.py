Agisci come un Senior Python Engineer. Riscrivi COMPLETAMENTE il file `app.py` da zero.
Il codice deve essere MONOLITICO (tutto in un unico file).

OBIETTIVO CRITICO DI RIFINITURA (SOLO BODY CV):
Migliorare la leggibilità della sezione Esperienze lavorative aggiungendo SPAZIO VUOTO (una riga) tra un'esperienza e l'altra.
TUTTO IL RESTO (Header Blu, Foto a Sx, Lettera, Sidebar) DEVE RIMANERE IDENTICO.

--- ISTRUZIONI RIGIDE CODICE ---

1. IMPORTS:
   Importa: `streamlit`, `google.generativeai`, `docx`, `PIL`, `io`, `datetime`.
   Importa da docx.shared: Inches, Pt, RGBColor.
   Importa da docx.enum.table: WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT.
   Importa da docx.enum.text: WD_ALIGN_PARAGRAPH.
   IMPORTANTE: Importa "from docx.oxml.ns import nsdecls" e "from docx.oxml import parse_xml".

2. CONFIGURAZIONE PAGINA:
   `st.set_page_config(page_title="Global Career Coach", layout="wide", initial_sidebar_state="expanded")`

3. INIZIALIZZAZIONE SESSION STATE:
   Se non esistono: `lang_code`='it', `generated_data`=None, `processed_photo`=None.

4. COSTANTI E DIZIONARI:

   A) LANG_DISPLAY (Invariato).
   B) TRANSLATIONS (Invariato).
   C) SECTION_TITLES (Invariato).

5. FUNZIONI HELPER:
   - `set_table_background`.
   - `add_bottom_border`.
   - `process_image`.
   - `get_todays_date`.

6. FUNZIONE `create_cv_docx` (LAYOUT AGGIORNATO SOLO NEL BODY):
   - **HEADER (CONGELATO):**
     - Tabella 1x2. Colonna Foto 1.2", Colonna Testo 6.1". Riga 2.0".
     - Sfondo Blu #20547D.
     - Foto a Sx, Centrata Vert.
     - Testo Bianco, Centrato Vert.
   
   - **BODY (MODIFICA SPAZI):**
     - Stampa Profilo.
     - Loop Sezioni:
       - Stampa Titolo + Linea Blu.
       - Se la sezione è una lista (come Esperienza/Formazione):
         - Itera sugli elementi.
         - Stampa l'elemento (Bullet point o testo normale).
         - **CRUCIALE:** SUBITO DOPO aver stampato l'elemento, aggiungi `doc.add_paragraph("")` (riga vuota) per staccarlo dal successivo.

7. FUNZIONE `create_letter_docx` (CONGELATA):
   - Mittente Sx, Data Sx, Destinatario Sx.
   - Oggetto Grassetto.
   - Firma: Saluti + 4 righe vuote + Nome.

8. LOGICA AI (SENZA TOOLS):
   - `model = genai.GenerativeModel("models/gemini-3-pro-preview")`.
   - Prompt: "Output JSON strictly in {selected_language}. Keys: personal_info, cv_sections, letter_data. NO NAME IN CLOSING."

9. MAIN LOOP:
   - Sidebar fissa.
   - Generazione.

Genera il codice `app.py` completo.
