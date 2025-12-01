import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageOps
import io
import json
import datetime
import urllib.parse
import pypdf
from serpapi import GoogleSearch  # NUOVA LIBRERIA PER RICERCA REALE

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
        width: 100%;
        cursor: pointer;
        font-weight: bold;
    }
    .job-card {
        padding: 20px;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin-bottom: 15px;
        background-color: #ffffff;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .job-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .job-card h4 { margin: 0 0 8px 0; color: #1F4E79; font-size: 18px; }
    .job-card .company { color: #555; font-weight: 600; margin-bottom: 10px; }
    .job-card .location { color: #777; font-size: 14px; margin-bottom: 10px; }
    .job-card a { 
        display: inline-block;
        background-color: #1F4E79;
        color: white !important;
        padding: 8px 15px;
        border-radius: 5px;
        text-decoration: none;
        font-size: 14px;
        margin-top: 5px;
    }
    .job-card a:hover { background-color: #163a5c; }
    </style>
""", unsafe_allow_html=True)

# --- 3. INIZIALIZZAZIONE SESSION STATE ---
if "lang_code" not in st.session_state:
    st.session_state.lang_code = "Italiano"
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None
if "processed_photo" not in st.session_state:
    st.session_state.processed_photo = None
if "job_search_results" not in st.session_state:
    st.session_state.job_search_results = None

# --- 4. COSTANTI E TRADUZIONI ---
LANG_DISPLAY = {
    "Italiano": "it", "English": "en", "Deutsch": "de", 
    "Español": "es", "Português": "pt"
}

SECTION_TITLES = {
    "it": {"exp": "ESPERIENZA PROFESSIONALE", "edu": "ISTRUZIONE E FORMAZIONE", "skills": "COMPETENZE", "lang": "LINGUE"},
    "en": {"exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS", "lang": "LANGUAGES"},
    "de": {"exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN", "lang": "SPRACHEN"},
    "es": {"exp": "EXPERIENCIA PROFESIONAL", "edu": "EDUCACIÓN", "skills": "HABILIDADES", "lang": "IDIOMAS"},
    "pt": {"exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skills": "COMPETÊNCIAS", "lang": "IDIOMAS"}
}

TRANSLATIONS = {
    "it": {
        "title": "Global Career Coach 🚀", "sub_cv": "1. Carica CV e Foto", 
        "sub_job": "2. Annuncio e Ricerca", "up_cv": "Carica CV (PDF)", 
        "up_ph": "Foto Profilo", "bord": "Bordo Foto", "rad": "Raggio (km)",
        "role": "Ruolo Target", "loc": "Città/Regione", "desc": "Incolla qui l'Annuncio di Lavoro",
        "btn_gen": "Genera Documenti", "btn_search": "Cerca Lavoro Live",
        "tab_cv": "CV Riscritto", "tab_cl": "Lettera", "tab_search": "Offerte Trovate",
        "warn_api": "Inserisci API Key nella Sidebar", "warn_data": "Carica CV e Annuncio",
        "loading": "Gemini 3 Pro al lavoro...", "searching": "Ricerca offerte reali...",
        "source_serp": "Fonte: Google Jobs (Live)", "source_smart": "Fonte: Smart Search (AI + Web)"
    },
    "en": {
        "title": "Global Career Coach 🚀", "sub_cv": "1. Upload CV & Photo", 
        "sub_job": "2. Job Ad & Search", "up_cv": "Upload CV (PDF)", 
        "up_ph": "Profile Photo", "bord": "Photo Border", "rad": "Radius (km)",
        "role": "Target Role", "loc": "City/Region", "desc": "Paste Job Description Here",
        "btn_gen": "Generate Docs", "btn_search": "Live Job Search",
        "tab_cv": "Rewritten CV", "tab_cl": "Cover Letter", "tab_search": "Found Jobs",
        "warn_api": "Enter API Key in Sidebar", "warn_data": "Upload CV and Job Ad",
        "loading": "Gemini 3 Pro working...", "searching": "Searching real jobs...",
        "source_serp": "Source: Google Jobs (Live)", "source_smart": "Source: Smart Search (AI + Web)"
    },
}
# Fallback
for l in ["de", "es", "pt"]: TRANSLATIONS[l] = TRANSLATIONS["en"]

# --- 5. FUNZIONI HELPER ---

def get_todays_date(lang):
    now = datetime.datetime.now()
    return now.strftime("%d.%m.%Y")

def extract_text_from_pdf(uploaded_file):
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
        return ""

def process_image(uploaded_img, border_size):
    if not uploaded_img: return None
    try:
        img = Image.open(uploaded_img)
        if img.mode != 'RGB': img = img.convert('RGB')
        if border_size > 0:
            img = ImageOps.expand(img, border=border_size, fill='white')
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception:
        return None

def set_table_background(table, color_hex):
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement('w:tblPr')
        table._tbl.insert(0, tbl_pr)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tbl_pr.append(shd)
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            cell_shd = OxmlElement('w:shd')
            cell_shd.set(qn('w:val'), 'clear')
            cell_shd.set(qn('w:color'), 'auto')
            cell_shd.set(qn('w:fill'), color_hex)
            tc_pr.append(cell_shd)

def add_bottom_border(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000') 
    pbdr.append(bottom)
    pPr.append(pbdr)

# --- 6. MOTORE DI RICERCA IBRIDO (SERPAPI + GEMINI FALLBACK) ---
def search_jobs_master(gemini_key, serp_key, role, location, lang):
    """
    Tenta la ricerca reale su Google Jobs tramite SerpApi.
    Se fallisce (o manca la chiave), usa Gemini + Python Link Construction.
    """
    
    # --- PIANO A: SERPAPI (Google Jobs Reale) ---
    if serp_key:
        try:
            params = {
                "engine": "google_jobs",
                "q": f"{role} {location}",
                "hl": lang, # Lingua interfaccia Google
                "api_key": serp_key
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            jobs = results.get("jobs_results", [])
            
            if jobs:
                formatted_jobs = []
                for job in jobs[:6]: # Primi 6 risultati
                    # Cerchiamo un link diretto se possibile
                    apply_link = "#"
                    if "apply_options" in job and len(job["apply_options"]) > 0:
                        apply_link = job["apply_options"][0]["link"]
                    elif "share_link" in job:
                        apply_link = job["share_link"]
                    else:
                        # Fallback link
                        q_enc = urllib.parse.quote(f"{job.get('title')} {job.get('company_name')} jobs")
                        apply_link = f"https://www.google.com/search?q={q_enc}"

                    formatted_jobs.append({
                        "company": job.get("company_name", "N/A"),
                        "role_title": job.get("title", role),
                        "link": apply_link,
                        "location": job.get("location", location),
                        "snippet": job.get("description", "")[:150] + "..."
                    })
                return formatted_jobs, "serp"
                
        except Exception as e:
            print(f"SerpApi Error (Fallback to Gemini): {e}")
            # Non blocchiamo, passiamo al Piano B

    # --- PIANO B: FALLBACK SMART (Gemini 2.0 Flash) ---
    # Se siamo qui, SerpApi ha fallito o la chiave mancava.
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("models/gemini-2.0-flash") # Veloce ed economico
        
        prompt = f"""
        Identify 5 real companies in '{location}' that are known to hire for '{role}' roles.
        Return ONLY a JSON array of strings (Company Names).
        Example: ["Company A", "Company B"]
        Do not include markdown formatting.
        """
        
        response = model.generate_content(prompt)
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        companies = json.loads(text_resp)
        
        smart_jobs = []
        for co in companies:
            # Costruzione Link Intelligente
            query = f"{role} jobs at {co} {location}"
            link = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            
            smart_jobs.append({
                "company": co,
                "role_title": f"{role} (Opportunity)",
                "link": link,
                "location": location,
                "snippet": f"Check open positions at {co} in {location}."
            })
            
        return smart_jobs, "smart"
        
    except Exception as e:
        return [], f"Error: {e}"

# --- 7. GENERATORE DOCUMENTI (GEMINI 3 PRO PREVIEW) ---
def generate_docs_ai(api_key, cv_text, job_text, lang):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-3-pro-preview")
    
    prompt = f"""
    Act as a Senior HR Resume Writer. Language: {lang}.
    
    INPUT:
    CV Text: {cv_text[:30000]}
    Job Ad: {job_text[:10000]}
    
    TASK:
    1. Extract Header Data (Name, Address, Phone, Email).
    2. Rewrite the CV Body professionally (Action-Oriented).
    3. Write a tailored Cover Letter.
    
    OUTPUT JSON (Strict):
    {{
        "header": {{ "name": "...", "address": "...", "phone": "...", "email": "..." }},
        "cv_body": [
            {{ "section": "PROFILE", "content": "..." }},
            {{ "section": "EXPERIENCE", "content": "..." }},
            {{ "section": "EDUCATION", "content": "..." }},
            {{ "section": "SKILLS", "content": "..." }}
        ],
        "cover_letter": "...full text..."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_resp)
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- 8. CREAZIONE WORD CV (LAYOUT BLU) ---
def create_cv_docx(data, photo_bytes, lang):
    doc = Document()
    
    # Layout Pagina
    section = doc.sections[0]
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.0)
    
    # --- HEADER BLU ---
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(1.5)
    table.columns[1].width = Inches(6.0)
    
    set_table_background(table, "20547D") # Blu richiesto
    
    # Foto (Sx)
    c_img = table.cell(0, 0)
    c_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_img = c_img.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if photo_bytes:
        r_img = p_img.add_run()
        r_img.add_picture(photo_bytes, width=Inches(1.2))
        
    # Testo (Dx)
    c_txt = table.cell(0, 1)
    c_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # Nome
    p_name = c_txt.paragraphs[0]
    r_name = p_name.add_run(data['header'].get('name', 'Name').upper())
    r_name.font.size = Pt(24)
    r_name.font.color.rgb = RGBColor(255, 255, 255)
    r_name.bold = True
    
    # Contatti
    info = f"{data['header'].get('address', '')} | {data['header'].get('phone', '')} | {data['header'].get('email', '')}"
    p_info = c_txt.add_paragraph(info)
    r_info = p_info.runs[0]
    r_info.font.size = Pt(10)
    r_info.font.color.rgb = RGBColor(255, 255, 255)
    
    doc.add_paragraph() # Spazio
    
    # --- BODY ---
    for sec in data.get('cv_body', []):
        # Titolo
        h = doc.add_paragraph()
        add_bottom_border(h)
        rh = h.add_run(sec['section'].upper())
        rh.font.size = Pt(12)
        rh.bold = True
        rh.font.color.rgb = RGBColor(32, 84, 125)
        
        # Contenuto
        doc.add_paragraph(sec['content'])
        doc.add_paragraph("") # Spazio extra richiesto

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 9. CREAZIONE WORD LETTERA ---
def create_letter_docx(text, data, lang):
    doc = Document()
    
    # Header
    doc.add_paragraph(data['header'].get('name', ''))
    doc.add_paragraph(data['header'].get('address', ''))
    doc.add_paragraph(data['header'].get('email', ''))
    doc.add_paragraph("\n")
    
    # Data
    doc.add_paragraph(get_todays_date(lang)).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph("\n")
    
    # Corpo
    doc.add_paragraph(text)
    doc.add_paragraph("\n\n")
    doc.add_paragraph("_______________________")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 10. MAIN APP ---
def main():
    # Setup Lingua
    lang_sel = st.sidebar.selectbox("Lingua / Language", list(LANG_DISPLAY.keys()))
    lang_iso = LANG_DISPLAY[lang_sel]
    txt = TRANSLATIONS[lang_iso]
    
    # Secrets
    gemini_key = st.secrets.get("GEMINI_API_KEY", None)
    serp_key = st.secrets.get("SERPAPI_API_KEY", None) # Opzionale, ma consigliata per ricerca reale
    
    if not gemini_key:
        gemini_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    # Sidebar
    st.sidebar.markdown(f"### {txt['sub_cv']}")
    up_ph = st.sidebar.file_uploader(txt['up_ph'], type=["jpg","png","jpeg"])
    bord = st.sidebar.slider(txt['bord'], 0, 50, 15)
    
    if up_ph:
        st.session_state.processed_photo = process_image(up_ph, bord)
        st.sidebar.image(st.session_state.processed_photo, width=150)
        
    st.sidebar.divider()
    
    # Job Search Sidebar
    st.sidebar.markdown(f"### {txt['sub_job']}")
    s_role = st.sidebar.text_input(txt['role'])
    s_loc = st.sidebar.text_input(txt['loc'])
    
    if st.sidebar.button(txt['btn_search']):
        if gemini_key and s_role and s_loc:
            with st.spinner(txt['searching']):
                res, mode = search_jobs_master(gemini_key, serp_key, s_role, s_loc, lang_iso)
                st.session_state.job_search_results = (res, mode)
        else:
            st.sidebar.error("Mancano dati per la ricerca")

    # Main
    st.title(txt['title'])
    
    c1, c2 = st.columns(2)
    with c1: f_cv = st.file_uploader(txt['up_cv'], type=["pdf"])
    with c2: job_ad = st.text_area(txt['desc'], height=150)
    
    if st.button(txt['btn_gen'], type="primary"):
        if gemini_key and f_cv and job_ad:
            with st.spinner(txt['loading']):
                raw_txt = extract_text_from_pdf(f_cv)
                data = generate_docs_ai(gemini_key, raw_txt, job_ad, lang_iso)
                if data:
                    st.session_state.generated_data = data
                    st.success("OK!")
        else:
            st.error(txt['warn_data'])
            
    # Tabs Risultati
    t1, t2, t3 = st.tabs([txt['tab_cv'], txt['tab_cl'], txt['tab_search']])
    
    with t1:
        if st.session_state.generated_data:
            st.json(st.session_state.generated_data.get('header'))
            docx = create_cv_docx(st.session_state.generated_data, st.session_state.processed_photo, lang_iso)
            st.download_button("⬇️ DOCX", docx, "CV_Pro.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
    with t2:
        if st.session_state.generated_data:
            cl = st.session_state.generated_data.get('cover_letter', '')
            st.markdown(cl)
            docx = create_letter_docx(cl, st.session_state.generated_data, lang_iso)
            st.download_button("⬇️ DOCX", docx, "CoverLetter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
    with t3:
        if st.session_state.job_search_results:
            res, mode = st.session_state.job_search_results
            label_src = txt['source_serp'] if mode == "serp" else txt['source_smart']
            st.caption(label_src)
            
            for j in res:
                st.markdown(f"""
                <div class="job-card">
                    <h4>{j['role_title']}</h4>
                    <div class="company">🏢 {j['company']} - 📍 {j.get('location', '')}</div>
                    <div style="font-size:0.9em; color:#666; margin-bottom:10px;">{j['snippet']}</div>
                    <a href="{j['link']}" target="_blank">👉 APPLICA SUBITO</a>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
