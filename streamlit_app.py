import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml
import io
import json
import datetime
import urllib.parse
from PIL import Image, ImageOps, ImageDraw
import pypdf
from serpapi import GoogleSearch

# -----------------------------------------------------------------------------
# 1. CONFIGURAZIONE PAGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. CSS INJECTION
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    .stButton button {
        cursor: pointer !important;
        font-weight: bold;
        border-radius: 8px;
    }
    .job-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        background-color: #f9f9f9;
        margin-bottom: 12px;
        transition: transform 0.2s;
    }
    .job-card:hover {
        transform: scale(1.01);
        border-color: #20547D;
    }
    .job-title {
        font-size: 18px;
        font-weight: bold;
        color: #20547D;
        margin-bottom: 4px;
    }
    .job-company {
        font-size: 15px;
        color: #333;
        font-weight: 500;
    }
    .job-meta {
        font-size: 12px;
        color: #666;
        margin-top: 8px;
        display: flex;
        justify-content: space-between;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. INIZIALIZZAZIONE SESSION STATE
# -----------------------------------------------------------------------------
if 'lang_code' not in st.session_state:
    st.session_state.lang_code = "Italiano"
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'processed_photo' not in st.session_state:
    st.session_state.processed_photo = None
if 'job_search_results' not in st.session_state:
    st.session_state.job_search_results = None

# -----------------------------------------------------------------------------
# 4. COSTANTI E DIZIONARI
# -----------------------------------------------------------------------------
LANG_DISPLAY = {
    "Italiano": "it", "English": "en", "Deutsch": "de", 
    "Español": "es", "Português": "pt"
}

SECTION_TITLES = {
    "it": {"exp": "ESPERIENZA PROFESSIONALE", "edu": "ISTRUZIONE", "skill": "COMPETENZE", "lang": "LINGUE", "info": "INFORMAZIONI PERSONALI"},
    "en": {"exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skill": "SKILLS", "lang": "LANGUAGES", "info": "PERSONAL DETAILS"},
    "de": {"exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skill": "FÄHIGKEITEN", "lang": "SPRACHEN", "info": "PERSÖNLICHE DATEN"},
    "es": {"exp": "EXPERIENCIA PROFESIONAL", "edu": "EDUCACIÓN", "skill": "HABILIDADES", "lang": "IDIOMAS", "info": "INFORMACIÓN PERSONAL"},
    "pt": {"exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skill": "HABILIDADES", "lang": "IDIOMAS", "info": "INFORMAÇÕES PESSOAIS"}
}

TRANSLATIONS = {
    "Italiano": {
        "title": "Global Career Coach 🚀",
        "tab_cv": "📄 Generazione Documenti",
        "tab_jobs": "🌍 Ricerca Lavoro",
        "lbl_role": "Ruolo desiderato",
        "lbl_loc": "Dove?",
        "lbl_rad": "Raggio (km)",
        "btn_search": "Cerca Offerte",
        "no_res": "Nessuna offerta trovata. Riprova.",
        "cv_up": "Carica CV (PDF)",
        "job_desc": "Incolla Annuncio (Opzionale per CV, Obbligatorio per Lettera)",
        "gen_btn": "Genera CV e Lettera",
        "photo_up": "Foto Profilo",
        "border": "Bordo Foto",
        "dl_cv": "Scarica CV (.docx)",
        "dl_let": "Scarica Lettera (.docx)",
        "wait": "Analisi e Scrittura con Gemini 3 Pro...",
        "success": "Documenti pronti!",
        "apply": "Candidati Ora 🚀",
        "source": "Fonte"
    },
    "English": {
        "title": "Global Career Coach 🚀",
        "tab_cv": "📄 Documents",
        "tab_jobs": "🌍 Job Search",
        "lbl_role": "Job Title",
        "lbl_loc": "Location",
        "lbl_rad": "Radius (km)",
        "btn_search": "Search Jobs",
        "no_res": "No jobs found.",
        "cv_up": "Upload CV (PDF)",
        "job_desc": "Paste Job Ad (Optional for CV, Required for Letter)",
        "gen_btn": "Generate Docs",
        "photo_up": "Profile Photo",
        "border": "Photo Border",
        "dl_cv": "Download CV (.docx)",
        "dl_let": "Download Letter (.docx)",
        "wait": "Processing with Gemini 3 Pro...",
        "success": "Ready!",
        "apply": "Apply Now 🚀",
        "source": "Source"
    },
    "Deutsch": {
        "title": "Global Career Coach 🚀",
        "tab_cv": "📄 Dokumente",
        "tab_jobs": "🌍 Jobsuche",
        "lbl_role": "Position",
        "lbl_loc": "Ort",
        "lbl_rad": "Radius",
        "btn_search": "Suchen",
        "no_res": "Keine Ergebnisse.",
        "cv_up": "CV hochladen (PDF)",
        "job_desc": "Stelleninserat (Pflicht für Anschreiben)",
        "gen_btn": "Generieren",
        "photo_up": "Profilbild",
        "border": "Rahmen",
        "dl_cv": "CV Laden (.docx)",
        "dl_let": "Brief Laden (.docx)",
        "wait": "Verarbeite mit Gemini 3 Pro...",
        "success": "Fertig!",
        "apply": "Jetzt Bewerben 🚀",
        "source": "Quelle"
    },
    "Español": {"title": "Global Career Coach", "tab_cv": "Documentos", "tab_jobs": "Buscar Empleo", "lbl_role": "Puesto", "lbl_loc": "Ubicación", "lbl_rad": "Radio", "btn_search": "Buscar", "no_res": "Sin resultados", "cv_up": "Subir CV", "job_desc": "Oferta", "gen_btn": "Generar", "photo_up": "Foto", "border": "Borde", "dl_cv": "Descargar CV", "dl_let": "Descargar Carta", "wait": "Procesando...", "success": "Hecho!", "apply": "Aplicar", "source": "Fuente"},
    "Português": {"title": "Global Career Coach", "tab_cv": "Documentos", "tab_jobs": "Buscar Vagas", "lbl_role": "Cargo", "lbl_loc": "Localização", "lbl_rad": "Raio", "btn_search": "Buscar", "no_res": "Sem resultados", "cv_up": "Enviar CV", "job_desc": "Anúncio", "gen_btn": "Gerar", "photo_up": "Foto", "border": "Borda", "dl_cv": "Baixar CV", "dl_let": "Baixar Carta", "wait": "Processando...", "success": "Pronto!", "apply": "Candidatar-se", "source": "Fonte"}
}

# -----------------------------------------------------------------------------
# 5. FUNZIONI HELPER
# -----------------------------------------------------------------------------

def get_todays_date(lang):
    now = datetime.datetime.now()
    if lang == "de": return now.strftime("%d.%m.%Y")
    if lang in ["en"]: return now.strftime("%B %d, %Y")
    return now.strftime("%d/%m/%Y")

def extract_text_from_pdf(uploaded_file):
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except:
        return ""

def process_image(uploaded_img, border_size):
    try:
        img = Image.open(uploaded_img).convert("RGBA")
        size = (min(img.size), min(img.size))
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        output = ImageOps.fit(img, size, centering=(0.5, 0.5))
        output.putalpha(mask)
        if border_size > 0:
            final_size = (size[0] + border_size * 2, size[1] + border_size * 2)
            bg = Image.new('RGBA', final_size, (0,0,0,0))
            draw_bg = ImageDraw.Draw(bg)
            draw_bg.ellipse((0, 0) + final_size, fill=(255,255,255,255))
            bg.paste(output, (border_size, border_size), output)
            return bg
        else:
            return output
    except:
        return None

# --- Word XML Helpers ---
def set_table_background(table, color_hex):
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), color_hex)
        tcPr.append(shd)

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

# -----------------------------------------------------------------------------
# 6. RICERCA LAVORO (SERPAPI MASTER + FALLBACK INTELLIGENTE)
# -----------------------------------------------------------------------------
def search_jobs_master(role, location, radius, lang_ui):
    results_list = []
    error_log = None

    # --- PIANO A: SERPAPI (Google Jobs Reale) ---
    try:
        serp_key = st.secrets.get("SERPAPI_API_KEY")
        if not serp_key:
            raise Exception("No SerpApi Key")

        search = GoogleSearch({
            "engine": "google_jobs",
            "q": f"{role} {location}",
            "hl": LANG_DISPLAY.get(lang_ui, "it"),
            "gl": "ch", # Switzerland base, modificabile
            "radius": radius,
            "api_key": serp_key
        })
        data = search.get_dict()
        
        if "jobs_results" not in data:
            raise Exception("No jobs from SerpApi")

        for job in data["jobs_results"][:10]: # Max 10 results
            # PRIORITÀ LINK: Apply Options > Share Link > Google Search Fallback
            final_link = ""
            apply_options = job.get("apply_options", [])
            
            if apply_options:
                final_link = apply_options[0].get("link")
            elif job.get("share_link"):
                final_link = job.get("share_link")
            else:
                # Fallback manuale pulito (senza virgolette)
                q_safe = urllib.parse.quote(f"{job.get('title')} {job.get('company_name')} {location} jobs")
                final_link = f"https://www.google.com/search?q={q_safe}"

            results_list.append({
                "title": job.get("title", "N/A"),
                "company": job.get("company_name", "N/A"),
                "location": job.get("location", location),
                "link": final_link,
                "source": "⚡ Live (SerpApi)"
            })
            
        return results_list

    except Exception as e:
        error_log = str(e)
        # Se SerpApi fallisce, procediamo al Piano B senza mostrare errore all'utente

    # --- PIANO B: AI FALLBACK (Google Search Links Puliti) ---
    try:
        gen_key = st.secrets.get("GEMINI_API_KEY")
        if not gen_key:
            return [{"title": "Errore", "company": "Chiavi Mancanti", "location": "", "link": "#", "source": "System"}]
        
        genai.configure(api_key=gen_key)
        # Usiamo il modello Flash per velocità nel fallback
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        prompt = f"""
        Act as a recruiter. Find 5 real companies hiring for '{role}' in '{location}'.
        Return ONLY a JSON array. Format:
        [{{"role_title": "...", "company": "...", "city": "..."}}]
        Do NOT invent.
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        jobs_ai = json.loads(text)
        
        for item in jobs_ai:
            # COSTRUZIONE LINK GOOGLE SICURA (SENZA VIRGOLETTE)
            # Query pulita: "Python Developer Google Zurich jobs"
            query_str = f"{item.get('role_title')} {item.get('company')} {location} jobs"
            safe_link = f"https://www.google.com/search?q={urllib.parse.quote(query_str)}"
            
            results_list.append({
                "title": item.get('role_title'),
                "company": item.get('company'),
                "location": item.get('city'),
                "link": safe_link,
                "source": "🤖 AI Suggestion"
            })
            
        return results_list

    except Exception as e:
        return [{"title": "Nessun risultato", "company": "Riprova con altri termini", "location": "", "link": "#", "source": "System"}]

# -----------------------------------------------------------------------------
# 7. FUNZIONI GENERAZIONE DOCUMENTI (WORD CONGELATO)
# -----------------------------------------------------------------------------

def create_cv_docx(data, photo_img):
    doc = Document()
    
    # Margini
    section = doc.sections[0]
    section.top_margin = Cm(1.0)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)

    # --- BANNER BLU (Tabella 1x2) ---
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Cm(4.5) # Colonna Foto
    table.columns[1].width = Cm(12.5) # Colonna Testo
    
    set_table_background(table, "20547D") # Blu richiesto

    # Cella 0: Foto
    cell_img = table.cell(0, 0)
    cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if photo_img:
        p = cell_img.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        img_byte = io.BytesIO()
        photo_img.save(img_byte, format="PNG")
        run.add_picture(img_byte, width=Cm(3.5))
    
    # Cella 1: Testo
    cell_txt = table.cell(0, 1)
    cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # Nome
    p1 = cell_txt.paragraphs[0]
    run1 = p1.add_run(f"{data.get('nome', '')}\n")
    run1.font.size = Pt(24)
    run1.font.color.rgb = RGBColor(255, 255, 255)
    run1.bold = True
    
    # Dati
    info_text = f"{data.get('indirizzo','')}\n{data.get('telefono','')} | {data.get('email','')}"
    p2 = cell_txt.add_paragraph(info_text)
    run2 = p2.runs[0]
    run2.font.size = Pt(10)
    run2.font.color.rgb = RGBColor(230, 230, 230)

    # Spazio dopo banner
    doc.add_paragraph().space_after = Pt(12)

    # --- CORPO DEL CV ---
    
    # Header helper
    def add_section_header(title):
        h = doc.add_paragraph(title)
        add_bottom_border(h)
        h.runs[0].bold = True
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        h.runs[0].font.size = Pt(12)
        h.runs[0].font.name = 'Calibri'

    # Sezione Dati Personali (se richiesto dal layout tedesco standard)
    labels = SECTION_TITLES.get("de", SECTION_TITLES["en"]) # Fallback
    
    if data.get('profilo'):
        add_section_header("PROFILO")
        doc.add_paragraph(data['profilo']).space_after = Pt(12)

    # Esperienza (Con spazio extra)
    if data.get('esperienze'):
        add_section_header(labels["exp"])
        for exp in data['esperienze']:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            r_tit = p.add_run(f"{exp.get('titolo','')} bei {exp.get('azienda','')}")
            r_tit.bold = True
            r_tit.font.size = Pt(11)
            
            p2 = doc.add_paragraph(f"{exp.get('date','')}")
            p2.runs[0].italic = True
            p2.runs[0].font.size = Pt(10)
            
            p3 = doc.add_paragraph(exp.get('descrizione',''))
            p3.runs[0].font.size = Pt(10.5)
            
            # SPAZIO VUOTO TRA ESPERIENZE (Richiesto)
            doc.add_paragraph("")

    # Istruzione
    if data.get('istruzione'):
        add_section_header(labels["edu"])
        for edu in data['istruzione']:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            r_tit = p.add_run(f"{edu.get('titolo','')}")
            r_tit.bold = True
            
            p2 = doc.add_paragraph(f"{edu.get('istituto','')}, {edu.get('date','')}")
            doc.add_paragraph("")

    # Skills
    if data.get('skills'):
        add_section_header(labels["skill"])
        p = doc.add_paragraph(", ".join(data['skills']))
        p.paragraph_format.space_before = Pt(6)

    return doc

def create_letter_docx(data, lang):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Mittente
    doc.add_paragraph(f"{data.get('nome','')}\n{data.get('email','')}\n{data.get('telefono','')}")
    doc.add_paragraph("")
    
    # Data
    doc.add_paragraph(get_todays_date(LANG_DISPLAY[lang]))
    doc.add_paragraph("")
    
    # Oggetto
    p_obj = doc.add_paragraph(f"Bewerbung als {data.get('ruolo_target','Position')}" if lang == "Deutsch" else f"Application for {data.get('ruolo_target','Position')}")
    p_obj.runs[0].bold = True
    doc.add_paragraph("")
    
    # Corpo
    doc.add_paragraph(data.get('lettera_corpo', ''))
    
    # Saluti e Firma
    doc.add_paragraph("\nFreundliche Grüsse,\n\n" if lang == "Deutsch" else "\nCordiali saluti,\n\n")
    doc.add_paragraph(data.get('nome',''))
    
    return doc

# -----------------------------------------------------------------------------
# 8. LOGICA AI (GEMINI 3 PRO PREVIEW)
# -----------------------------------------------------------------------------
def generate_docs_ai(cv_text, job_desc, lang):
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    if not gemini_key: return None

    genai.configure(api_key=gemini_key)
    # MODELLO SPECIFICO
    model = genai.GenerativeModel("models/gemini-3-pro-preview")

    prompt = f"""
    You are an expert Career Coach. Analyze the CV and Job Description.
    Target Language: {lang}.
    
    INPUT CV TEXT: {cv_text[:4000]}
    INPUT JOB AD: {job_desc}
    
    OUTPUT JSON FORMAT (Strictly):
    {{
        "nome": "Name Surname",
        "indirizzo": "Address",
        "telefono": "Phone",
        "email": "Email",
        "profilo": "Professional Summary (3-4 lines)",
        "ruolo_target": "Job Title from Ad",
        "esperienze": [
            {{"titolo": "Job Title", "azienda": "Company", "date": "Date Range", "descrizione": "Bullet points"}}
        ],
        "istruzione": [
            {{"titolo": "Degree", "istituto": "School", "date": "Date"}}
        ],
        "skills": ["Skill1", "Skill2", "Skill3"],
        "lettera_corpo": "Full body of cover letter (no header/footer). Professional tone."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# -----------------------------------------------------------------------------
# 9. MAIN UI LOOP
# -----------------------------------------------------------------------------
def main():
    if 'lang_code' not in st.session_state: st.session_state.lang_code = "Italiano"
    t_code = st.session_state.lang_code
    t = TRANSLATIONS[t_code]

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Config")
        st.session_state.lang_code = st.selectbox("Lingua / Language", list(TRANSLATIONS.keys()))
        
        st.divider()
        st.subheader(t["photo_up"])
        uploaded_img = st.file_uploader("Foto", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        border_size = st.slider(t["border"], 0, 20, 5)
        
        if uploaded_img:
            proc_img = process_image(uploaded_img, border_size)
            st.session_state.processed_photo = proc_img
            st.image(proc_img, width=150)

    # --- HEADER ---
    st.title(t["title"])

    # --- TABS ---
    tab1, tab2 = st.tabs([t["tab_cv"], t["tab_jobs"]])

    # *** TAB 1: DOCUMENT GENERATOR ***
    with tab1:
        col_up, col_txt = st.columns([1, 1])
        with col_up:
            f_pdf = st.file_uploader(t["cv_up"], type=["pdf"])
        with col_txt:
            job_txt = st.text_area(t["job_desc"], height=150)

        if st.button(t["gen_btn"], type="primary"):
            if not f_pdf:
                st.error("CV PDF Missing")
            else:
                with st.spinner(t["wait"]):
                    cv_text = extract_text_from_pdf(f_pdf)
                    data = generate_docs_ai(cv_text, job_txt, t_code)
                    if data:
                        st.session_state.generated_data = data
                        st.success(t["success"])
        
        # Download Section
        if st.session_state.generated_data:
            st.divider()
            col_d1, col_d2 = st.columns(2)
            
            docx_cv = create_cv_docx(st.session_state.generated_data, st.session_state.processed_photo)
            bio_cv = io.BytesIO()
            docx_cv.save(bio_cv)
            
            docx_let = create_letter_docx(st.session_state.generated_data, t_code)
            bio_let = io.BytesIO()
            docx_let.save(bio_let)
            
            with col_d1:
                st.download_button(t["dl_cv"], bio_cv.getvalue(), "CV_Optimized.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            with col_d2:
                st.download_button(t["dl_let"], bio_let.getvalue(), "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # *** TAB 2: JOB SEARCH (SERPAPI + AI LINK FIX) ***
    with tab2:
        c1, c2, c3 = st.columns([2, 2, 1])
        role = c1.text_input(t["lbl_role"])
        loc = c2.text_input(t["lbl_loc"], value="Zürich, CH")
        rad = c3.number_input(t["lbl_rad"], value=20)
        
        if st.button(t["btn_search"]):
            with st.spinner("Searching..."):
                res = search_jobs_master(role, loc, rad, t_code) # Use t_code (Italiano, English...)
                st.session_state.job_search_results = res

        # Display Results
        jobs = st.session_state.job_search_results
        if jobs:
            if isinstance(jobs, dict) and "error" in jobs: # Handle explicit API errors
                 st.error(f"API Error: {jobs['error']}")
            elif len(jobs) == 0:
                st.info(t["no_res"])
            else:
                for job in jobs:
                    # Card UI
                    st.markdown(f"""
                    <div class="job-card">
                        <div class="job-title">{job['title']}</div>
                        <div class="job-company">{job['company']} - {job['location']}</div>
                        <div class="job-meta">
                            <span>{t["source"]}: {job['source']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button(t["apply"], job['link'])

if __name__ == "__main__":
    main()
