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
        cursor: pointer;
        font-weight: bold;
    }
    .job-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        background-color: #f9f9f9;
        margin-bottom: 10px;
    }
    .job-title {
        font-size: 18px;
        font-weight: bold;
        color: #20547D;
    }
    .job-company {
        font-size: 14px;
        color: #555;
        margin-bottom: 5px;
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
    "it": {"exp": "ESPERIENZA PROFESSIONALE", "edu": "ISTRUZIONE", "skill": "COMPETENZE", "lang": "LINGUE"},
    "en": {"exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skill": "SKILLS", "lang": "LANGUAGES"},
    "de": {"exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skill": "FÄHIGKEITEN", "lang": "SPRACHEN"},
    "es": {"exp": "EXPERIENCIA PROFESIONAL", "edu": "EDUCACIÓN", "skill": "HABILIDADES", "lang": "IDIOMAS"},
    "pt": {"exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skill": "HABILIDADES", "lang": "IDIOMAS"}
}

TRANSLATIONS = {
    "Italiano": {
        "title": "Global Career Coach 🚀",
        "tab_cv": "📄 Generazione Documenti",
        "tab_jobs": "🌍 Ricerca Lavoro (Live)",
        "lbl_role": "Ruolo desiderato",
        "lbl_loc": "Dove?",
        "lbl_rad": "Raggio (km)",
        "btn_search": "Cerca Offerte Reali",
        "no_res": "Nessuna offerta trovata. Prova a cambiare parametri.",
        "cv_up": "Carica CV (PDF)",
        "job_desc": "Incolla Annuncio (Opzionale per CV, Obbligatorio per Lettera)",
        "gen_btn": "Genera CV e Lettera",
        "photo_up": "Foto Profilo",
        "border": "Bordo Foto",
        "dl_cv": "Scarica CV (.docx)",
        "dl_let": "Scarica Lettera (.docx)",
        "wait": "Analisi e Scrittura con Gemini 3 Pro...",
        "success": "Documenti pronti!",
        "apply": "Candidati Ora 🚀"
    },
    "English": {
        "title": "Global Career Coach 🚀",
        "tab_cv": "📄 Document Generation",
        "tab_jobs": "🌍 Job Search (Live)",
        "lbl_role": "Job Title",
        "lbl_loc": "Location",
        "lbl_rad": "Radius (km)",
        "btn_search": "Search Real Jobs",
        "no_res": "No jobs found. Try adjusting parameters.",
        "cv_up": "Upload CV (PDF)",
        "job_desc": "Paste Job Ad (Optional for CV, Required for Letter)",
        "gen_btn": "Generate CV & Letter",
        "photo_up": "Profile Photo",
        "border": "Photo Border",
        "dl_cv": "Download CV (.docx)",
        "dl_let": "Download Letter (.docx)",
        "wait": "Analyzing and Writing with Gemini 3 Pro...",
        "success": "Documents ready!",
        "apply": "Apply Now 🚀"
    },
    # Aggiungere altre lingue se necessario (Deutsch, Español, Português mappati su Inglese per brevità in questo snippet)
    "Deutsch": {"title": "Global Career Coach", "tab_cv": "Dokumente", "tab_jobs": "Jobsuche", "lbl_role": "Position", "lbl_loc": "Ort", "lbl_rad": "Radius", "btn_search": "Suchen", "no_res": "Keine Ergebnisse", "cv_up": "CV hochladen", "job_desc": "Stellenanzeige", "gen_btn": "Generieren", "photo_up": "Foto", "border": "Rand", "dl_cv": "CV Laden", "dl_let": "Brief Laden", "wait": "Bitte warten...", "success": "Fertig!", "apply": "Bewerben"},
    "Español": {"title": "Global Career Coach", "tab_cv": "Documentos", "tab_jobs": "Buscar Empleo", "lbl_role": "Puesto", "lbl_loc": "Ubicación", "lbl_rad": "Radio", "btn_search": "Buscar", "no_res": "Sin resultados", "cv_up": "Subir CV", "job_desc": "Oferta", "gen_btn": "Generar", "photo_up": "Foto", "border": "Borde", "dl_cv": "Descargar CV", "dl_let": "Descargar Carta", "wait": "Espere...", "success": "Hecho!", "apply": "Aplicar"},
    "Português": {"title": "Global Career Coach", "tab_cv": "Documentos", "tab_jobs": "Buscar Vagas", "lbl_role": "Cargo", "lbl_loc": "Localização", "lbl_rad": "Raio", "btn_search": "Buscar", "no_res": "Sem resultados", "cv_up": "Enviar CV", "job_desc": "Anúncio", "gen_btn": "Gerar", "photo_up": "Foto", "border": "Borda", "dl_cv": "Baixar CV", "dl_let": "Baixar Carta", "wait": "Aguarde...", "success": "Pronto!", "apply": "Candidatar-se"}
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
    """Ritaglia la foto a cerchio e aggiunge bordo."""
    try:
        img = Image.open(uploaded_img).convert("RGBA")
        
        # Ritaglio circolare
        size = (min(img.size), min(img.size))
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        
        output = ImageOps.fit(img, size, centering=(0.5, 0.5))
        output.putalpha(mask)
        
        # Aggiunta bordo se > 0
        if border_size > 0:
            final_size = (size[0] + border_size * 2, size[1] + border_size * 2)
            bg = Image.new('RGBA', final_size, (0,0,0,0)) # Trasparente
            
            # Disegna cerchio bordo (bianco o colorato, qui usiamo bianco per contrasto su blu)
            draw_bg = ImageDraw.Draw(bg)
            draw_bg.ellipse((0, 0) + final_size, fill=(255,255,255,255))
            
            # Incolla foto al centro
            bg.paste(output, (border_size, border_size), output)
            return bg
        else:
            return output
    except:
        return None

# --- Word XML Helpers ---
def set_table_background(table, color_hex):
    """Imposta il colore di sfondo per l'intera tabella (o celle specifiche)."""
    # In questo caso coloriamo tutte le celle della prima riga
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), color_hex)
        tcPr.append(shd)

def add_bottom_border(paragraph):
    """Aggiunge una linea nera sottile sotto il paragrafo."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6') # 1/8 pt
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pbdr.append(bottom)
    pPr.append(pbdr)

# -----------------------------------------------------------------------------
# 6. FUNZIONE SEARCH JOBS (SERPAPI MASTER)
# -----------------------------------------------------------------------------
def search_jobs_master(role, location, radius, lang_ui):
    """
    Cerca lavori usando SerpApi e estrae i link di candidatura REALI.
    """
    serp_key = st.secrets.get("SERPAPI_API_KEY")
    if not serp_key:
        return {"error": "Chiave SerpApi mancante nei Secrets."}

    params = {
        "engine": "google_jobs",
        "q": f"{role} {location}",
        "hl": LANG_DISPLAY.get(lang_ui, "it"), # Lingua interfaccia Google
        "gl": "ch", # Geolocalizzazione base (Svizzera come default o dinamico)
        "radius": radius,
        "api_key": serp_key
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        jobs_data = []
        if "jobs_results" in results:
            for job in results["jobs_results"]:
                # --- LOGICA ESTRAZIONE LINK DIRETTO ---
                link = ""
                apply_options = job.get("apply_options", [])
                
                if apply_options:
                    # Prende il primo link disponibile (solitamente il più diretto)
                    link = apply_options[0].get("link")
                else:
                    # Fallback sul link di condivisione se non ci sono opzioni
                    link = job.get("share_link", "#")

                jobs_data.append({
                    "title": job.get("title", "N/A"),
                    "company": job.get("company_name", "N/A"),
                    "location": job.get("location", ""),
                    "description": job.get("description", "")[:200] + "...",
                    "link": link, # Link pulito
                    "platform": apply_options[0].get("title") if apply_options else "Google Jobs"
                })
        
        return jobs_data

    except Exception as e:
        return {"error": str(e)}

# -----------------------------------------------------------------------------
# 7. FUNZIONI GENERAZIONE DOCUMENTI (WORD)
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
    # Profilo
    if data.get('profilo'):
        h = doc.add_paragraph("PROFILO")
        add_bottom_border(h)
        h.runs[0].bold = True
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        doc.add_paragraph(data['profilo']).space_after = Pt(12)

    # Esperienza
    if data.get('esperienze'):
        h = doc.add_paragraph("ESPERIENZA PROFESSIONALE")
        add_bottom_border(h)
        h.runs[0].bold = True
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        for exp in data['esperienze']:
            p = doc.add_paragraph()
            r_tit = p.add_run(f"{exp.get('titolo','')} - {exp.get('azienda','')}")
            r_tit.bold = True
            p.add_run(f"\n{exp.get('date','')}\n{exp.get('descrizione','')}")
            doc.add_paragraph("") # Spazio vuoto

    # Istruzione
    if data.get('istruzione'):
        h = doc.add_paragraph("ISTRUZIONE")
        add_bottom_border(h)
        h.runs[0].bold = True
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        for edu in data['istruzione']:
            p = doc.add_paragraph()
            r_tit = p.add_run(f"{edu.get('titolo','')}")
            r_tit.bold = True
            p.add_run(f"\n{edu.get('istituto','')}, {edu.get('date','')}")
            doc.add_paragraph("")

    # Skills
    if data.get('skills'):
        h = doc.add_paragraph("COMPETENZE")
        add_bottom_border(h)
        h.runs[0].bold = True
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        doc.add_paragraph(", ".join(data['skills']))

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
    p_obj = doc.add_paragraph(f"Oggetto: Candidatura per {data.get('ruolo_target','Posizione')}")
    p_obj.runs[0].bold = True
    doc.add_paragraph("")
    
    # Corpo
    doc.add_paragraph(data.get('lettera_corpo', ''))
    
    # Saluti e Firma
    doc.add_paragraph("\nCordiali saluti,\n\n\n") # Spazio firma
    doc.add_paragraph(data.get('nome',''))
    
    return doc

# -----------------------------------------------------------------------------
# 8. LOGICA AI (GEMINI 3 PRO PREVIEW)
# -----------------------------------------------------------------------------
def generate_docs_ai(cv_text, job_desc, lang):
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    if not gemini_key: return None

    genai.configure(api_key=gemini_key)
    # MODELLO SPECIFICO RICHIESTO
    model = genai.GenerativeModel("models/gemini-3-pro-preview")

    # Prompt JSON Strutturato
    prompt = f"""
    Sei un Career Coach esperto. Analizza il CV e l'Annuncio.
    Lingua Output: {lang}.
    
    INPUT CV: {cv_text[:3000]}...
    INPUT JOB: {job_desc}
    
    RESTITUISCI SOLO UN JSON (no markdown) con questa struttura esatta:
    {{
        "nome": "Nome Cognome",
        "indirizzo": "Città, Paese",
        "telefono": "+...",
        "email": "...",
        "profilo": "Breve riassunto professionale...",
        "ruolo_target": "Titolo del lavoro dell'annuncio",
        "esperienze": [
            {{"titolo": "...", "azienda": "...", "date": "...", "descrizione": "Punti elenco..."}}
        ],
        "istruzione": [
            {{"titolo": "...", "istituto": "...", "date": "..."}}
        ],
        "skills": ["Skill1", "Skill2"],
        "lettera_corpo": "Testo completo della lettera di presentazione, diviso in paragrafi, convincente e mirata."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Errore AI: {e}")
        return None

# -----------------------------------------------------------------------------
# 9. MAIN UI LOOP
# -----------------------------------------------------------------------------
def main():
    t_code = st.session_state.lang_code
    t = TRANSLATIONS[t_code]

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Config")
        st.session_state.lang_code = st.selectbox("Lingua", list(TRANSLATIONS.keys()))
        
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

    # *** TAB 1: GENERATORE ***
    with tab1:
        col_up, col_txt = st.columns([1, 1])
        with col_up:
            f_pdf = st.file_uploader(t["cv_up"], type=["pdf"])
        with col_txt:
            job_txt = st.text_area(t["job_desc"], height=150)

        if st.button(t["gen_btn"], type="primary"):
            if not f_pdf:
                st.error("Manca il PDF del CV.")
            else:
                with st.spinner(t["wait"]):
                    cv_text = extract_text_from_pdf(f_pdf)
                    # Chiamata AI
                    data = generate_docs_ai(cv_text, job_txt, t_code)
                    
                    if data:
                        st.session_state.generated_data = data
                        st.success(t["success"])
        
        # Download Area
        if st.session_state.generated_data:
            st.divider()
            col_d1, col_d2 = st.columns(2)
            
            # Crea DOCX CV
            docx_cv = create_cv_docx(st.session_state.generated_data, st.session_state.processed_photo)
            bio_cv = io.BytesIO()
            docx_cv.save(bio_cv)
            
            # Crea DOCX Lettera
            docx_let = create_letter_docx(st.session_state.generated_data, t_code)
            bio_let = io.BytesIO()
            docx_let.save(bio_let)
            
            with col_d1:
                st.download_button(
                    label=t["dl_cv"],
                    data=bio_cv.getvalue(),
                    file_name="CV_Optimized.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            with col_d2:
                st.download_button(
                    label=t["dl_let"],
                    data=bio_let.getvalue(),
                    file_name="Cover_Letter.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    # *** TAB 2: JOB SEARCH (SERPAPI) ***
    with tab2:
        c1, c2, c3 = st.columns([2, 2, 1])
        role = c1.text_input(t["lbl_role"])
        loc = c2.text_input(t["lbl_loc"], value="Zurich, CH")
        rad = c3.number_input(t["lbl_rad"], value=20)
        
        if st.button(t["btn_search"]):
            with st.spinner("Searching..."):
                results = search_jobs_master(role, loc, rad, LANG_DISPLAY[t_code])
                st.session_state.job_search_results = results

        # Visualizzazione Risultati
        res = st.session_state.job_search_results
        if res:
            if isinstance(res, dict) and "error" in res:
                st.error(f"Errore SerpApi: {res['error']}")
            elif len(res) == 0:
                st.info(t["no_res"])
            else:
                for job in res:
                    # Card Layout
                    st.markdown(f"""
                    <div class="job-card">
                        <div class="job-title">{job['title']}</div>
                        <div class="job-company">{job['company']} - {job['location']}</div>
                        <div style="font-size:12px; color:#777; margin-bottom:10px;">
                            Fonte: {job['platform']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    # Link diretto
                    st.link_button(t["apply"], job['link'])

if __name__ == "__main__":
    main()
