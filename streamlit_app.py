import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import qn
import io
import datetime
import json
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
        transition: transform 0.2s;
    }
    .search-card:hover {
        transform: scale(1.01);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    a { text-decoration: none; font-weight: bold; color: #0066cc; }
    </style>
""", unsafe_allow_html=True)

# --- 3. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state.lang_code = 'it'
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'processed_photo' not in st.session_state:
    st.session_state.processed_photo = None
if 'job_search_results' not in st.session_state:
    st.session_state.job_search_results = None
if 'pdf_ref' not in st.session_state:
    st.session_state.pdf_ref = None

# --- 4. COSTANTI E DIZIONARI ---
LANG_DISPLAY = {
    "Italiano": "it", "English": "en", "Deutsch": "de", 
    "Español": "es", "Français": "fr", "Português": "pt"
}

TRANSLATIONS = {
    "it": {
        "title": "Global Career Coach", 
        "sb_photo": "Foto Profilo", "sb_job": "Ricerca Lavoro",
        "role_in": "Ruolo Target", "loc_in": "Città/Regione", "rad_in": "Raggio (km)", 
        "search_btn": "🔎 Cerca Offerte", "upload_first": "⚠️ Carica prima il tuo CV nel pannello principale!",
        "main_upload": "1. Carica il tuo CV (PDF)", "main_results": "2. Risultati Ricerca",
        "main_gen": "3. Generazione Documenti", "job_desc_in": "Incolla qui l'Annuncio di Lavoro",
        "gen_btn": "✨ Genera CV e Lettera",
        "download_cv": "Scarica CV (.docx)", "download_cl": "Scarica Lettera (.docx)",
        "missing_key": "Chiave API mancante", "processing": "Elaborazione in corso...", "searching": "Ricerca live su Google..."
    },
    "en": {
        "title": "Global Career Coach", 
        "sb_photo": "Profile Photo", "sb_job": "Job Search",
        "role_in": "Target Role", "loc_in": "City/Region", "rad_in": "Radius (km)", 
        "search_btn": "🔎 Search Jobs", "upload_first": "⚠️ Upload your CV in the main panel first!",
        "main_upload": "1. Upload your CV (PDF)", "main_results": "2. Search Results",
        "main_gen": "3. Document Generation", "job_desc_in": "Paste Job Description here",
        "gen_btn": "✨ Generate Docs",
        "download_cv": "Download CV (.docx)", "download_cl": "Download Letter (.docx)",
        "missing_key": "Missing API Key", "processing": "Processing...", "searching": "Live Google search..."
    },
    "de": {
        "title": "Global Career Coach", 
        "sb_photo": "Profilbild", "sb_job": "Jobsuche",
        "role_in": "Zielposition", "loc_in": "Stadt/Region", "rad_in": "Radius (km)", 
        "search_btn": "🔎 Jobs suchen", "upload_first": "⚠️ Bitte laden Sie zuerst Ihren Lebenslauf hoch!",
        "main_upload": "1. Lebenslauf hochladen (PDF)", "main_results": "2. Suchergebnisse",
        "main_gen": "3. Dokumentenerstellung", "job_desc_in": "Stellenanzeige hier einfügen",
        "gen_btn": "✨ Dokumente erstellen",
        "download_cv": "CV herunterladen (.docx)", "download_cl": "Anschreiben herunterladen (.docx)",
        "missing_key": "API Key fehlt", "processing": "Verarbeitung...", "searching": "Live-Suche auf Google..."
    }
}

SECTION_TITLES = {
    "it": {"exp": "ESPERIENZA PROFESSIONALE", "edu": "ISTRUZIONE", "skill": "COMPETENZE"},
    "en": {"exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skill": "SKILLS"},
    "de": {"exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skill": "KENNTNISSE"}
}

# --- 5. FUNZIONI HELPER ---

def get_todays_date(lang):
    now = datetime.datetime.now()
    if lang == 'de': return now.strftime("%d. %B %Y")
    if lang == 'it': return now.strftime("%d/%m/%Y")
    return now.strftime("%B %d, %Y")

def clean_json_string(s):
    return s.replace("```json", "").replace("```", "").strip()

def set_table_background(cell, color_hex):
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def add_bottom_border(paragraph):
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
        try:
            img = Image.open(uploaded_file)
            img = ImageOps.exif_transpose(img)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_with_border = ImageOps.expand(img, border=int(border_width), fill='white')
            img_byte_arr = io.BytesIO()
            img_with_border.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr.seek(0)
            return img_byte_arr
        except:
            return None
    return None

def extract_text_from_pdf(file):
    try:
        import pypdf
        reader = pypdf.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])
    except:
        return ""

# --- 6. FUNZIONI AI CORE ---

def search_jobs_live(api_key, role, location, radius, lang):
    """
    Esegue SOLO la ricerca live con Google Search Retrieval.
    Nessuna allucinazione o link inventati.
    """
    genai.configure(api_key=api_key)
    
    try:
        # Configurazione Tool Ricerca
        tools = [{'google_search_retrieval': {}}]
        model = genai.GenerativeModel("models/gemini-2.0-flash", tools=tools)
        
        prompt = f"""
        Find 5 ACTIVE and REAL job postings for the role '{role}' in '{location}' (radius {radius} km).
        Current Date: {datetime.datetime.now().strftime('%Y-%m-%d')}.
        Language: {lang}.
        
        Return a JSON list with this EXACT schema:
        [
            {{
                "company": "Company Name",
                "role_title": "Role Title",
                "link": "REAL_URL_ONLY",
                "snippet": "Short description"
            }}
        ]
        IMPORTANT: verify links are real. If no active jobs found, return empty list [].
        """
        
        response = model.generate_content(prompt)
        if not response.text: return []
        
        json_str = clean_json_string(response.text)
        return json.loads(json_str)

    except Exception as e:
        st.error(f"Search Error: {str(e)}")
        return []

def generate_docs_ai(api_key, cv_text, job_desc, lang):
    genai.configure(api_key=api_key)
    # Usiamo Gemini 3 Pro per la scrittura (No Tools)
    model = genai.GenerativeModel("models/gemini-3-pro-preview")
    
    prompt = f"""
    Role: Professional Career Coach. Language: {lang}.
    
    Task:
    1. Extract User Data from CV (Name, Email, Phone, Address).
    2. Rewrite CV (Professional summary, Experience, Education, Skills) to match the Job Description. Use action verbs.
    3. Write a tailored Cover Letter for the Job Description.
    
    Input CV: {cv_text[:15000]}
    Job Description: {job_desc[:5000]}
    
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

# --- 7. FUNZIONI DOCX (CONGELATE) ---

def create_cv_docx(data, photo_bytes, lang_code='it'):
    doc = Document()
    
    # Header Blu
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(1.5)
    table.columns[1].width = Inches(5.0)
    
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    row.height = Inches(2.0)
    
    cell_photo = row.cells[0]
    cell_info = row.cells[1]
    
    set_table_background(cell_photo, "20547D")
    set_table_background(cell_info, "20547D")
    
    if photo_bytes:
        try:
            p = cell_photo.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(io.BytesIO(photo_bytes), width=Inches(1.2))
        except: pass
        
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
    titles = SECTION_TITLES.get(lang_code, SECTION_TITLES['en'])
    
    # Profilo
    h = doc.add_heading('PROFILO', level=1)
    add_bottom_border(h)
    doc.add_paragraph(cv.get('summary', ''))
    
    # Esperienza
    h = doc.add_heading(titles['exp'], level=1)
    add_bottom_border(h)
    for exp in cv.get('experience', []):
        p = doc.add_paragraph()
        run = p.add_run(f"{exp.get('title')} at {exp.get('company')}")
        run.bold = True
        doc.add_paragraph(f"{exp.get('period')}")
        doc.add_paragraph(exp.get('details'))
        doc.add_paragraph("")
        
    # Skills
    h = doc.add_heading(titles['skill'], level=1)
    add_bottom_border(h)
    doc.add_paragraph(cv.get('skills', ''))
    
    # Education
    h = doc.add_heading(titles['edu'], level=1)
    add_bottom_border(h)
    doc.add_paragraph(cv.get('education', ''))
    
    return doc

def create_letter_docx(data, lang_code='it'):
    doc = Document()
    ud = data.get('user_data', {})
    
    doc.add_paragraph(ud.get('name', ''))
    doc.add_paragraph(ud.get('email', ''))
    doc.add_paragraph(ud.get('phone', ''))
    doc.add_paragraph(get_todays_date(lang_code))
    doc.add_paragraph("")
    
    doc.add_paragraph(data.get('cover_letter', ''))
    
    doc.add_paragraph("")
    doc.add_paragraph("Cordiali Saluti,")
    doc.add_paragraph("")
    doc.add_paragraph(ud.get('name', ''))
    
    return doc

# --- 11. MAIN LOOP ---

api_key = st.text_input("🔑 Google Gemini API Key", type="password")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Impostazioni")
    lang_sel = st.selectbox("Lingua", list(LANG_DISPLAY.keys()))
    st.session_state.lang_code = LANG_DISPLAY[lang_sel]
    t = TRANSLATIONS[st.session_state.lang_code if st.session_state.lang_code in TRANSLATIONS else 'en']
    
    st.divider()
    st.subheader(f"📸 {t['sb_photo']}")
    u_photo = st.file_uploader("Upload Foto", type=['jpg','png'])
    border = st.slider("Bordo", 0, 10, 2)
    if u_photo:
        processed = process_image(u_photo, border)
        st.session_state.processed_photo = processed.getvalue()
        st.image(processed, caption="Anteprima")
        
    st.divider()
    st.subheader(f"💼 {t['sb_job']}")
    s_role = st.text_input(t['role_in'])
    s_loc = st.text_input(t['loc_in'])
    s_rad = st.slider(t['rad_in'], 10, 100, 50)
    
    # BOTTONE RICERCA (BLOCCO SICUREZZA)
    if st.button(t['search_btn']):
        if not st.session_state.pdf_ref:
            st.error(t['upload_first']) # BLOCCA SE NO PDF
        elif not api_key:
            st.error(t['missing_key'])
        elif not s_role or not s_loc:
            st.warning("Inserisci Ruolo e Città")
        else:
            with st.spinner(t['searching']):
                res = search_jobs_live(api_key, s_role, s_loc, s_rad, st.session_state.lang_code)
                st.session_state.job_search_results = res

# --- MAIN PAGE ---
st.title(t['title'])

# SEZIONE 1: UPLOAD CV (OBBLIGATORIO)
st.subheader(t['main_upload'])
uploaded_cv = st.file_uploader("Upload CV", type=['pdf'], label_visibility="collapsed")

if uploaded_cv:
    st.session_state.pdf_ref = uploaded_cv # SALVA RIFERIMENTO PDF
    st.success("✅ PDF Caricato")
else:
    st.session_state.pdf_ref = None
    st.info("Carica il tuo CV per abilitare la ricerca lavoro.")

st.divider()

# SEZIONE 2: RISULTATI RICERCA (SOLO SE PRESENTI)
if st.session_state.job_search_results:
    st.subheader(t['main_results'])
    
    if len(st.session_state.job_search_results) == 0:
        st.warning("Nessuna offerta trovata.")
    else:
        for job in st.session_state.job_search_results:
            with st.container():
                st.markdown(f"""
                <div class="search-card">
                    <h4>{job.get('role_title', 'Job')} @ {job.get('company', 'Company')}</h4>
                    <p>{job.get('snippet', '')}</p>
                    <a href="{job.get('link', '#')}" target="_blank">🔗 VAI ALL'OFFERTA</a>
                </div>
                """, unsafe_allow_html=True)
    st.divider()

# SEZIONE 3: GENERAZIONE DOCUMENTI
st.subheader(t['main_gen'])
job_desc_text = st.text_area(t['job_desc_in'], height=200)

if st.button(t['gen_btn']):
    if not api_key or not uploaded_cv or not job_desc_text:
        st.error(t['missing_data'])
    else:
        with st.spinner(t['processing']):
            cv_text = extract_text_from_pdf(uploaded_cv)
            data = generate_docs_ai(api_key, cv_text, job_desc_text, st.session_state.lang_code)
            st.session_state.generated_data = data
            st.success("Documenti pronti!")

# DOWNLOAD AREA
if st.session_state.generated_data:
    col_d1, col_d2 = st.columns(2)
    
    # Docx CV
    doc_cv = create_cv_docx(st.session_state.generated_data, st.session_state.processed_photo, st.session_state.lang_code)
    bio_cv = io.BytesIO()
    doc_cv.save(bio_cv)
    
    with col_d1:
        st.download_button(
            t['download_cv'], 
            bio_cv.getvalue(), 
            "CV_Optimized.docx", 
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    # Docx Lettera
    doc_cl = create_letter_docx(st.session_state.generated_data, st.session_state.lang_code)
    bio_cl = io.BytesIO()
    doc_cl.save(bio_cl)
    
    with col_d2:
        st.download_button(
            t['download_cl'], 
            bio_cl.getvalue(), 
            "CoverLetter.docx", 
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
