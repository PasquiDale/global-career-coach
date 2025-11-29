import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import qn
import io
import json
import datetime
import urllib.parse
from PIL import Image, ImageOps

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS INJECTION ---
st.markdown("""
    <style>
    .stButton>button {
        cursor: pointer;
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .search-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
    a { text-decoration: none; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state.lang_code = 'it'
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'processed_photo' not in st.session_state:
    st.session_state.processed_photo = None
if 'job_search_results' not in st.session_state:
    st.session_state.job_search_results = None

# --- 4. COSTANTI E DIZIONARI ---
LANG_DISPLAY = {
    "Italiano": "it", "English": "en", "Deutsch": "de", 
    "Español": "es", "Français": "fr", "Português": "pt"
}

TRANSLATIONS = {
    "it": {
        "title": "Global Career Coach", "role_in": "Ruolo Target", "loc_in": "Città/Regione",
        "rad_in": "Raggio (km)", "search_btn": "🔎 Cerca Lavoro (Live)", 
        "gen_btn": "✨ Genera Documenti", "tab_cv": "Curriculum", "tab_cl": "Lettera", "tab_job": "Offerte",
        "missing_key": "Chiave API mancante", "missing_data": "Carica PDF e compila i campi",
        "processing": "Analisi in corso...", "searching": "Scansione del web...",
        "fallback_msg": "Ricerca Live non disponibile. Generazione Smart Links.",
        "download_cv": "Scarica CV (.docx)", "download_cl": "Scarica Lettera (.docx)"
    },
    "en": {
        "title": "Global Career Coach", "role_in": "Target Role", "loc_in": "City/Region",
        "rad_in": "Radius (km)", "search_btn": "🔎 Search Jobs (Live)", 
        "gen_btn": "✨ Generate Docs", "tab_cv": "Resume", "tab_cl": "Cover Letter", "tab_job": "Jobs",
        "missing_key": "Missing API Key", "missing_data": "Upload PDF and fill fields",
        "processing": "Processing...", "searching": "Scanning the web...",
        "fallback_msg": "Live Search unavailable. Generating Smart Links.",
        "download_cv": "Download CV (.docx)", "download_cl": "Download Letter (.docx)"
    },
    "de": {
        "title": "Global Career Coach", "role_in": "Zielposition", "loc_in": "Stadt/Region",
        "rad_in": "Radius (km)", "search_btn": "🔎 Jobsuche (Live)", 
        "gen_btn": "✨ Dokumente Erstellen", "tab_cv": "Lebenslauf", "tab_cl": "Anschreiben", "tab_job": "Jobs",
        "missing_key": "API Key fehlt", "missing_data": "PDF hochladen und Felder ausfüllen",
        "processing": "Verarbeitung...", "searching": "Web-Scan läuft...",
        "fallback_msg": "Live-Suche nicht verfügbar. Erstelle Smart Links.",
        "download_cv": "CV Herunterladen (.docx)", "download_cl": "Anschreiben Herunterladen (.docx)"
    }
}

# --- 5. FUNZIONI HELPER ---

def get_todays_date(lang):
    now = datetime.datetime.now()
    if lang == 'de': return now.strftime("%d. %B %Y")
    if lang == 'it': return now.strftime("%d/%m/%Y")
    return now.strftime("%B %d, %Y")

def clean_json_string(s):
    """Pulisce la stringa JSON dai backticks di markdown"""
    return s.replace("```json", "").replace("```", "").strip()

def set_table_background(cell, color_hex):
    """Imposta lo sfondo di una cella DOCX"""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def add_bottom_border(paragraph):
    """Aggiunge una linea sotto il paragrafo"""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'auto')
    pbdr.append(bottom)
    pPr.append(pbdr)

def process_image(uploaded_file, border_width):
    if uploaded_file:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img) # Fix rotazione
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Creiamo un bordo bianco
        img_with_border = ImageOps.expand(img, border=int(border_width), fill='white')
        
        # Salviamo in bytes per il docx
        img_byte_arr = io.BytesIO()
        img_with_border.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    return None

def extract_text_from_pdf(file):
    try:
        import pypdf
        reader = pypdf.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])
    except:
        return ""

# --- 6. FUNZIONE SEARCH JOBS (CRITICA) ---

def search_jobs_live(api_key, role, location, radius, lang):
    """
    Tenta la ricerca live con Google Search Retrieval.
    Se fallisce, usa Smart Links generati.
    """
    genai.configure(api_key=api_key)
    results_list = []
    
    # TENTATIVO 1: LIVE SEARCH (SINTASSI CORRETTA)
    try:
        # Sintassi ufficiale per il tool di ricerca
        tools = [{'google_search_retrieval': {}}]
        
        # Usiamo Flash 2.0 perché supporta i tool ed è veloce
        model = genai.GenerativeModel("models/gemini-2.0-flash", tools=tools)
        
        prompt = f"""
        Find 5 ACTIVE and RECENT job postings for the role '{role}' in '{location}' (within {radius} km).
        Current Date: {datetime.datetime.now().strftime('%Y-%m-%d')}.
        Language: {lang}.
        
        Return a JSON list with this EXACT schema:
        [
            {{
                "company": "Company Name",
                "role_title": "Exact Role Title",
                "link": "THE_REAL_URL_FOUND",
                "snippet": "Brief description"
            }}
        ]
        Verify that the links are real job postings if possible.
        Only return the JSON list, no text.
        """
        
        response = model.generate_content(prompt)
        # Pulizia JSON
        json_str = clean_json_string(response.text)
        results_list = json.loads(json_str)
        
        # Se la lista è vuota o il link è finto, solleviamo eccezione per andare al fallback
        if not results_list or "google.com" in results_list[0].get('link', ''):
            raise Exception("No valid live links found")
            
        return results_list, "LIVE"

    except Exception as e:
        # TENTATIVO 2: FALLBACK (SMART LINKS)
        # Se il tool fallisce, chiediamo a Gemini solo i nomi delle aziende
        # e costruiamo noi i link di ricerca Google.
        
        print(f"Live Search Error: {e}") # Debug console
        
        try:
            model_fallback = genai.GenerativeModel("models/gemini-2.0-flash") # No tools
            
            fallback_prompt = f"""
            Identify 5 companies in '{location}' that typically hire for '{role}'.
            Return a JSON list:
            [
                {{ "company": "Company Name", "role_title": "{role}" }}
            ]
            """
            
            resp = model_fallback.generate_content(fallback_prompt)
            data = json.loads(clean_json_string(resp.text))
            
            # Costruzione Smart Links
            smart_results = []
            for item in data:
                comp = item.get('company', 'Unknown')
                title = item.get('role_title', role)
                # Creiamo un link di ricerca Google
                query = f"jobs {title} at {comp} {location}"
                encoded_query = urllib.parse.quote(query)
                smart_link = f"https://www.google.com/search?q={encoded_query}"
                
                smart_results.append({
                    "company": comp,
                    "role_title": title,
                    "link": smart_link,
                    "snippet": "Smart Search Link generated by AI"
                })
            
            return smart_results, "SMART_FALLBACK"
            
        except Exception as e2:
            return [], f"ERROR: {str(e2)}"

# --- 7. FUNZIONE GENERAZIONE DOCUMENTI ---

def generate_docs_ai(api_key, cv_text, role, location, lang):
    genai.configure(api_key=api_key)
    
    # Usiamo il modello potente per la scrittura
    model = genai.GenerativeModel("models/gemini-3-pro-preview")
    
    prompt = f"""
    Role: Career Coach. Language: {lang}.
    Target Role: {role} in {location}.
    
    Input CV: {cv_text[:10000]}
    
    Task:
    1. Extract User Data (Name, Email, Phone, Address).
    2. Rewrite CV body (Professional summary, Experience, Education, Skills). Make it action-oriented.
    3. Write a Cover Letter for the target role.
    
    Return JSON:
    {{
        "user_data": {{ "name": "...", "email": "...", "phone": "...", "address": "..." }},
        "cv_content": {{
            "summary": "...",
            "experience": [ {{ "title": "...", "company": "...", "period": "...", "details": "..." }} ],
            "education": "...",
            "skills": "..."
        }},
        "cover_letter": "..."
    }}
    """
    
    response = model.generate_content(prompt)
    return json.loads(clean_json_string(response.text))

# --- 8. FUNZIONI DOCX (CONGELATE) ---

def create_cv_docx(data, photo_bytes):
    doc = Document()
    
    # Header Blu #20547D (Tabella 1x2)
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(1.5) # Foto
    table.columns[1].width = Inches(5.0) # Testo
    
    row = table.rows[0]
    cell_photo = row.cells[0]
    cell_info = row.cells[1]
    
    set_table_background(cell_photo, "20547D")
    set_table_background(cell_info, "20547D")
    
    # Foto
    if photo_bytes:
        try:
            p = cell_photo.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(io.BytesIO(photo_bytes), width=Inches(1.2))
        except: pass
        
    # Info Testo
    ud = data.get('user_data', {})
    p = cell_info.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cell_info.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    name_run = p.add_run(f"{ud.get('name', 'Name')}\n")
    name_run.font.size = Pt(24)
    name_run.font.color.rgb = RGBColor(255, 255, 255)
    name_run.bold = True
    
    details = f"{ud.get('address', '')} | {ud.get('phone', '')} | {ud.get('email', '')}"
    det_run = p.add_run(details)
    det_run.font.size = Pt(10)
    det_run.font.color.rgb = RGBColor(230, 230, 230)
    
    doc.add_paragraph().space_after = Pt(10)
    
    # Body
    cv = data.get('cv_content', {})
    
    # Profilo
    h = doc.add_heading('PROFILO', level=1)
    add_bottom_border(h)
    doc.add_paragraph(cv.get('summary', ''))
    
    # Esperienza
    h = doc.add_heading('ESPERIENZA', level=1)
    add_bottom_border(h)
    for exp in cv.get('experience', []):
        p = doc.add_paragraph()
        run = p.add_run(f"{exp.get('title')} at {exp.get('company')}")
        run.bold = True
        doc.add_paragraph(f"{exp.get('period')}")
        doc.add_paragraph(exp.get('details'))
        doc.add_paragraph("") # Spazio
        
    # Skills
    h = doc.add_heading('COMPETENZE', level=1)
    add_bottom_border(h)
    doc.add_paragraph(cv.get('skills', ''))
    
    return doc

def create_letter_docx(data):
    doc = Document()
    ud = data.get('user_data', {})
    
    # Intestazione
    doc.add_paragraph(ud.get('name', ''))
    doc.add_paragraph(ud.get('email', ''))
    doc.add_paragraph(ud.get('phone', ''))
    doc.add_paragraph(datetime.datetime.now().strftime("%d/%m/%Y"))
    doc.add_paragraph("")
    
    # Corpo
    doc.add_paragraph(data.get('cover_letter', ''))
    
    # Firma
    doc.add_paragraph("")
    doc.add_paragraph("Cordiali Saluti,")
    doc.add_paragraph("")
    doc.add_paragraph("")
    doc.add_paragraph(ud.get('name', ''))
    
    return doc

# --- 9. INTERFACCIA UTENTE ---

api_key = st.text_input("🔑 Google Gemini API Key", type="password")

# Sidebar
with st.sidebar:
    st.header("Impostazioni")
    lang_sel = st.selectbox("Lingua", list(LANG_DISPLAY.keys()))
    st.session_state.lang_code = LANG_DISPLAY[lang_sel]
    t = TRANSLATIONS[st.session_state.lang_code if st.session_state.lang_code in TRANSLATIONS else 'en']
    
    st.subheader("Foto")
    u_photo = st.file_uploader("Upload Foto", type=['jpg','png'])
    border = st.slider("Bordo", 0, 10, 2)
    if u_photo:
        processed = process_image(u_photo, border)
        st.session_state.processed_photo = processed.getvalue()
        st.image(processed, caption="Anteprima")

# Main
st.title(t['title'])

# Input Dati
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    role = st.text_input(t['role_in'])
with col2:
    loc = st.text_input(t['loc_in'])
with col3:
    rad = st.number_input(t['rad_in'], value=50)

uploaded_cv = st.file_uploader("Upload CV (PDF)", type=['pdf'])

# Tabs
tab_job, tab_cv, tab_cl = st.tabs([f"🔎 {t['tab_job']}", f"📄 {t['tab_cv']}", f"✉️ {t['tab_cl']}"])

# TAB RICERCA (Live Browsing)
with tab_job:
    if st.button(t['search_btn']):
        if not api_key:
            st.error(t['missing_key'])
        elif not role or not loc:
            st.warning("Inserisci Ruolo e Città")
        else:
            with st.spinner(t['searching']):
                res, mode = search_jobs_live(api_key, role, loc, rad, st.session_state.lang_code)
                st.session_state.job_search_results = (res, mode)
    
    # Visualizzazione Risultati
    if st.session_state.job_search_results:
        results, mode = st.session_state.job_search_results
        
        if mode == "SMART_FALLBACK":
            st.warning(t['fallback_msg'])
            st.info("💡 Suggerimento: Clicca sui link per aprire la ricerca Google pre-impostata.")
        
        for job in results:
            with st.container():
                st.markdown(f"""
                <div class="search-card">
                    <h4>{job.get('role_title', 'Job')} @ {job.get('company', 'Company')}</h4>
                    <p>{job.get('snippet', '')}</p>
                    <a href="{job.get('link', '#')}" target="_blank">🔗 VAI ALL'OFFERTA</a>
                </div>
                """, unsafe_allow_html=True)

# TAB GENERAZIONE DOCUMENTI
with tab_cv:
    if st.button(t['gen_btn']):
        if not api_key or not uploaded_cv:
            st.error(t['missing_data'])
        else:
            with st.spinner(t['processing']):
                cv_text = extract_text_from_pdf(uploaded_cv)
                data = generate_docs_ai(api_key, cv_text, role, loc, st.session_state.lang_code)
                st.session_state.generated_data = data
                st.success("OK!")

    if st.session_state.generated_data:
        # Download CV
        doc_cv = create_cv_docx(st.session_state.generated_data, st.session_state.processed_photo)
        bio_cv = io.BytesIO()
        doc_cv.save(bio_cv)
        st.download_button(t['download_cv'], bio_cv.getvalue(), "CV.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        # Preview JSON (Debug visivo)
        st.json(st.session_state.generated_data['cv_content'])

with tab_cl:
    if st.session_state.generated_data:
        # Download Lettera
        doc_cl = create_letter_docx(st.session_state.generated_data)
        bio_cl = io.BytesIO()
        doc_cl.save(bio_cl)
        st.download_button(t['download_cl'], bio_cl.getvalue(), "CoverLetter.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        st.write(st.session_state.generated_data.get('cover_letter', ''))
