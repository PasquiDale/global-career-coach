Agisci come un Senior Python Engineer esperto in `python-docx`.
Dobbiamo sistemare definitivamente il LAYOUT WORD e le TRADUZIONI.

PROBLEMI DA RISOLVERE:
1. WORD: La foto nel banner blu è allineata in alto. DEVE essere ALLINEATA VERTICALMENTE AL CENTRO.
2. LINGUA: L'utente trova titoli in Italiano/Francese anche se seleziona Tedesco. I titoli delle sezioni (Esperienza, Skills, ecc.) devono essere tradotti rigorosamente via codice.

ISTRUZIONI TECNICHE AVANZATE:

1. DIZIONARIO TITOLI SEZIONI (Hardcoded):
   - Crea un dizionario Python `SECTION_TITLES` che contiene le traduzioni per le 7 lingue supportate.
   - Chiavi: 'profile', 'experience', 'education', 'skills', 'contact'.
   - Esempio per Tedesco (CH):
     `'de_ch': {'profile': 'PROFIL', 'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KOMPETENZEN'}`.
   - Usa questo dizionario per scrivere i titoli nel file Word (NON farli generare all'AI, così siamo sicuri siano nella lingua giusta).

2. ALLINEAMENTO VERTICALE WORD (Fix Critico):
   - Importa: `from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT`.
   - Quando crei la tabella del banner (header):
     - `cell_foto = table.cell(0, 0)`
     - `cell_testo = table.cell(0, 1)`
     - IMPONI: `cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER`
     - IMPONI: `cell_testo.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER`
   - Questo obbligherà la foto a stare esattamente al centro del banner blu.

3. LOGICA GENERAZIONE CONTENUTO (AI):
   - Usa sempre `models/gemini-3-pro-preview`.
   - Prompt: Chiedi un JSON *puro* con i dati. Specifica chiaramente: "Il contenuto dei campi (descrizioni, ruoli) deve essere scritto in {selected_language}."
   - L'AI riempie il contenuto, Python mette i titoli tradotti corretti.

4. FORMATTAZIONE SEZIONI (Design):
   - Per ogni sezione (es. 'BERUFSERFAHRUNG'):
     - Scrivi il titolo in BLU (#20547d), MAIUSCOLO, GRASSETTO.
     - Aggiungi un bordo inferiore al paragrafo del titolo (border-bottom) per fare la linea divisoria elegante.

OUTPUT:
- Codice `app.py` completo.
- `requirements.txt`.
