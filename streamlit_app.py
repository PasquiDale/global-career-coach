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
import pypdf  # SOSTITUZIONE CRITICA DI PYPDF2

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
    }
    .job-card {
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
    .job-card h4 { margin: 0 0 5px 0; color: #1F4E79; }
    .job-card a { color: #d9534f; text-decoration: none; font-weight: bold; }
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
        "loading": "Elaborazione con Gemini...", "searching": "Scansione web in corso..."
    },
    "en": {
        "title": "Global Career Coach 🚀", "sub_cv": "1. Upload CV & Photo", 
        "sub_job": "2. Job Ad & Search", "up_cv": "Upload CV (PDF)", 
        "up_ph": "Profile Photo", "bord": "Photo Border", "rad": "Radius (km)",
        "role": "Target Role", "loc": "City/Region", "desc": "Paste Job Description Here",
        "btn_gen": "Generate Docs", "btn_search": "Live Job Search",
        "tab_cv": "Rewritten CV", "tab_cl": "Cover Letter", "tab_search": "Found Jobs",
        "warn_api": "Enter API Key in Sidebar", "warn_data": "Upload CV and Job Ad",
        "loading": "Processing with Gemini...", "searching": "Scanning the web..."
    },
    # (Aggiungere de, es, pt per brevità se necessario, ma la logica è identica)
}
# Fallback per lingue mancanti nel dizionario sopra per brevità
for l in ["de", "es", "pt"]:
    TRANSLATIONS[l] = TRANSLATIONS["en"]

# --- 5. FUNZIONI HELPER ---

def get_todays_date(lang):
    now = datetime.datetime.now()
    return now.strftime("%d.%m.%Y")

def extract_text_from_pdf(uploaded_file):
    """Estrae testo usando pypdf (versione stabile)."""
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
    """Elabora l'immagine con PIL."""
    if not uploaded_img: return None
    try:
        img = Image.open(uploaded_img)
        if img.mode != 'RGB': img = img.convert('RGB')
        # Aggiunge bordo bianco
        if border_size > 0:
            img = ImageOps.expand(img, border=border_size, fill='white')
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception:
        return None

def set_table_background(table, color_hex):
    """Imposta sfondo blu per la tabella header."""
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement('w:tblPr')
        table._tbl.insert(0, tbl_pr)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tbl_pr.append(shd)
    # Applica a tutte le celle
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            cell_shd = OxmlElement('w:shd')
            cell_shd.set(qn('w:val'), 'clear')
            cell_shd.set(qn('w:color'), 'auto')
            cell_shd.set(qn('w:fill'), color_hex)
            tc_pr.append(cell_shd)

def add_bottom_border(paragraph):
    """Aggiunge la linea sotto i titoli."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000') # Nero
    pbdr.append(bottom)
    pPr.append(pbdr)

# --- 6. FUNZIONE SEARCH JOBS LIVE ---
def search_jobs_live(api_key, role, location, radius, lang):
    """
    Tenta la ricerca live con Gemini 2.0 Flash Tools.
    Fallback: Smart Links generati via Python.
    """
    genai.configure(api_key=api_key)
    
    # TENTATIVO 1: LIVE SEARCH con Tools
    try:
        tools = [{'google_search_retrieval': {}}]
        # Modello specifico per ricerca veloce
        model = genai.GenerativeModel("models/gemini-2.0-flash", tools=tools)
        
        prompt = f"""
        Find 5 ACTIVE and REAL job postings for the role '{role}' in '{location}' (within {radius} km).
        Current Date: {datetime.datetime.now().strftime('%Y-%m-%d')}.
        
        Strictly output a JSON list of objects with these keys:
        - "company": Company Name
        - "role_title": Exact Role Title
        - "link": The direct URL to the job posting (verify it exists)
        - "snippet": A very short description (max 10 words)
        
        Example: [{{"company": "Google", "role_title": "Software Eng", "link": "https://...", "snippet": "..."}}]
        """
        
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        # Pulizia JSON
        if "```json" in text_resp:
            text_resp = text_resp.split("```json")[1].split("```")[0]
        elif "```" in text_resp:
            text_resp = text_resp.split("```")[1].split("```")[0]
            
        results = json.loads(text_resp)
        return results, "Live Search (Gemini 2.0)"

    except Exception as e:
        # TENTATIVO 2: FALLBACK SMART LINKS
        # Se fallisce il tool, usiamo l'AI per trovare aziende e Python per i link
        try:
            model_fallback = genai.GenerativeModel("models/gemini-2.0-flash") # No tools
            prompt_fallback = f"""
            Identify 5 companies in '{location}' that typically hire for '{role}'.
            Return ONLY a JSON list of strings (Company Names).
            Example: ["Company A", "Company B"]
            """
            response = model_fallback.generate_content(prompt_fallback)
            text_resp = response.text.strip()
            if "```" in text_resp:
                text_resp = text_resp.replace("```json", "").replace("```", "")
            
            company_names = json.loads(text_resp)
            
            # Costruiamo i link manualmente (Smart Links)
            smart_results = []
            for co in company_names:
                query = f"{role} {co} {location} jobs"
                encoded_query = urllib.parse.quote(query)
                google_url = f"https://www.google.com/search?q={encoded_query}"
                smart_results.append({
                    "company": co,
                    "role_title": f"{role} (Search)",
                    "link": google_url,
                    "snippet": "Click to search for open positions"
                })
            
            return smart_results, "Smart Links (Fallback)"
            
        except Exception as e2:
            return [], f"Error: {str(e2)}"

# --- 7. LOGICA GENERAZIONE DOCUMENTI ---
def generate_docs_ai(api_key, cv_text, job_text, lang):
    genai.configure(api_key=api_key)
    
    # Modello 3.0 Pro Preview per alta qualità scrittura
    model = genai.GenerativeModel("models/gemini-3-pro-preview")
    
    prompt = f"""
    Act as a Professional HR Resume Writer. Language: {lang}.
    
    INPUT:
    CV Text: {cv_text[:20000]}
    Job Ad: {job_text[:5000]}
    
    TASK:
    1. Extract Header Info (Name, Address, Email, Phone).
    2. Rewrite the CV body. Use professional Action Verbs. Structure: Summary, Experience, Education, Skills.
    3. Write a Cover Letter tailored to the Job Ad.
    
    OUTPUT JSON FORMAT (Strict):
    {{
        "header": {{ "name": "...", "address": "...", "email": "...", "phone": "..." }},
        "cv_body": [
            {{ "section": "PROFILE", "content": "..." }},
            {{ "section": "EXPERIENCE", "content": "role at company..." }},
            {{ "section": "EDUCATION", "content": "..." }},
            {{ "section": "SKILLS", "content": "..." }}
        ],
        "cover_letter": "Full text of cover letter..."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_resp)
    except Exception as e:
        st.error(f"AI Generation Error: {e}")
        return None

# --- 8. CREAZIONE WORD CV (HEADER BLU) ---
def create_cv_docx(data, photo_bytes, lang):
    doc = Document()
    
    # Margini stretti per massimizzare spazio
    section = doc.sections[0]
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.0)
    
    # HEADER TABELLA (Sfondo Blu #20547D)
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(1.5) # Colonna Foto
    table.columns[1].width = Inches(6.0) # Colonna Testo
    
    set_table_background(table, "20547D") # Blu scuro
    
    # Cella Foto
    cell_img = table.cell(0, 0)
    cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_img = cell_img.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if photo_bytes:
        run_img = p_img.add_run()
        run_img.add_picture(photo_bytes, width=Inches(1.2))
        
    # Cella Testo
    cell_txt = table.cell(0, 1)
    cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # Nome
    p_name = cell_txt.paragraphs[0]
    run_name = p_name.add_run(data['header'].get('name', 'Name').upper())
    run_name.font.size = Pt(24)
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    run_name.bold = True
    
    # Dati Contatto
    contact_info = f"{data['header'].get('address', '')} | {data['header'].get('phone', '')} | {data['header'].get('email', '')}"
    p_contact = cell_txt.add_paragraph(contact_info)
    run_contact = p_contact.runs[0]
    run_contact.font.size = Pt(10)
    run_contact.font.color.rgb = RGBColor(255, 255, 255)
    
    doc.add_paragraph() # Spazio dopo header
    
    # BODY
    for section in data.get('cv_body', []):
        # Titolo Sezione
        h = doc.add_paragraph()
        add_bottom_border(h)
        run_h = h.add_run(section['section'].upper())
        run_h.font.size = Pt(12)
        run_h.bold = True
        run_h.font.color.rgb = RGBColor(32, 84, 125) # Blu simile header
        
        # Contenuto
        p = doc.add_paragraph(section['content'])
        p.paragraph_format.space_after = Pt(12)
        
        # Spaziatura extra richiesta
        doc.add_paragraph("") 

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 9. CREAZIONE WORD LETTERA ---
def create_letter_docx(text, data, lang):
    doc = Document()
    
    # Intestazione
    doc.add_paragraph(data['header'].get('name', ''))
    doc.add_paragraph(data['header'].get('address', ''))
    doc.add_paragraph(data['header'].get('email', ''))
    doc.add_paragraph(data['header'].get('phone', ''))
    doc.add_paragraph("\n")
    
    # Data
    doc.add_paragraph(get_todays_date(lang)).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph("\n")
    
    # Corpo
    doc.add_paragraph(text)
    doc.add_paragraph("\n\n")
    
    # Firma
    doc.add_paragraph("_______________________")
    doc.add_paragraph(data['header'].get('name', ''))
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 10. MAIN APP LOOP ---

def main():
    # Gestione Lingua
    lang_sel = st.sidebar.selectbox("Lingua / Language", list(LANG_DISPLAY.keys()))
    lang_iso = LANG_DISPLAY[lang_sel]
    txt = TRANSLATIONS[lang_iso]
    
    # API Key
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        api_key = st.sidebar.text_input("API Key", type="password")
        
    # Sidebar Inputs
    st.sidebar.markdown(f"### {txt['sub_cv']}")
    uploaded_photo = st.sidebar.file_uploader(txt["up_ph"], type=["jpg", "png", "jpeg"])
    border_val = st.sidebar.slider(txt["bord"], 0, 50, 15)
    
    # Processing Foto Live
    if uploaded_photo:
        st.session_state.processed_photo = process_image(uploaded_photo, border_val)
        st.sidebar.image(st.session_state.processed_photo, width=150)
        
    st.sidebar.divider()
    
    # Job Search Sidebar
    st.sidebar.markdown(f"### {txt['sub_job']}")
    search_role = st.sidebar.text_input(txt["role"])
    search_loc = st.sidebar.text_input(txt["loc"])
    search_rad = st.sidebar.slider(txt["rad"], 10, 100, 30)
    
    if st.sidebar.button(txt["btn_search"]):
        if api_key and search_role and search_loc:
            with st.spinner(txt["searching"]):
                res, method = search_jobs_live(api_key, search_role, search_loc, search_rad, lang_sel)
                st.session_state.job_search_results = (res, method)
        else:
            st.sidebar.error("Mancano dati o API Key")

    # Main Content
    st.title(txt["title"])
    
    # Input CV e Annuncio
    col1, col2 = st.columns(2)
    with col1:
        f_cv = st.file_uploader(txt["up_cv"], type=["pdf"])
    with col2:
        job_ad_text = st.text_area(txt["desc"], height=150)

    # Bottone Generazione
    if st.button(txt["btn_gen"], type="primary"):
        if not api_key:
            st.error(txt["warn_api"])
        elif not f_cv or not job_ad_text:
            st.error(txt["warn_data"])
        else:
            with st.spinner(txt["loading"]):
                raw_text = extract_text_from_pdf(f_cv)
                data = generate_docs_ai(api_key, raw_text, job_ad_text, lang_sel)
                if data:
                    st.session_state.generated_data = data
                    st.success("OK!")

    # Output Tabs
    t1, t2, t3 = st.tabs([txt["tab_cv"], txt["tab_cl"], txt["tab_search"]])
    
    # Tab 1: CV
    with t1:
        if st.session_state.generated_data:
            # Anteprima testo veloce
            st.json(st.session_state.generated_data.get('header'))
            
            # Generazione Word
            docx_cv = create_cv_docx(
                st.session_state.generated_data, 
                st.session_state.processed_photo,
                lang_sel
            )
            
            st.download_button(
                label=f"⬇️ {txt['tab_cv']} (.docx)",
                data=docx_cv,
                file_name="CV_Optimized.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    # Tab 2: Lettera
    with t2:
        if st.session_state.generated_data:
            cl_text = st.session_state.generated_data.get('cover_letter', '')
            st.markdown(cl_text)
            
            docx_cl = create_letter_docx(
                cl_text,
                st.session_state.generated_data,
                lang_sel
            )
            
            st.download_button(
                label=f"⬇️ {txt['tab_cl']} (.docx)",
                data=docx_cl,
                file_name="Cover_Letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # Tab 3: Risultati Ricerca
    with t3:
        if st.session_state.job_search_results:
            results, method = st.session_state.job_search_results
            st.caption(f"Source: {method}")
            
            for job in results:
                st.markdown(
                    f"""
                    <div class="job-card">
                        <h4>{job.get('role_title')} @ {job.get('company')}</h4>
                        <p>{job.get('snippet', '')}</p>
                        <a href="{job.get('link')}" target="_blank">👉 APPLICA ORA / VAI AL SITO</a>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

if __name__ == "__main__":
    main()
