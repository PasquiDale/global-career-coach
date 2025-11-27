import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import json
import pypdf
import re
import base64
from PIL import Image, ImageOps

# --- 1. CONFIGURAZIONE PAGINA (PRIMA ISTRUZIONE ASSOLUTA) ---
st.set_page_config(
    page_title="Global Career Coach", 
    page_icon="👔", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. INIZIALIZZAZIONE SESSION STATE (ANTI-CRASH) ---
if "lang_code" not in st.session_state:
    st.session_state.lang_code = "it"
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None
if "processed_photo" not in st.session_state:
    st.session_state.processed_photo = None

# CSS per pulizia interfaccia
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    .stFileUploader label {font-size: 90%;}
    .stImage {border: 1px solid #ddd; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# --- 3. DIZIONARI E COSTANTI ---

LANG_MAP = {
    "Italiano": "it",
    "English (UK)": "en_uk",
    "English (US)": "en_us",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

# Traduzioni Complete (Chiavi unificate)
TRANSLATIONS = {
    "it": {
        "sidebar_title": "Impostazioni Profilo", "lang_label": "Seleziona Lingua", 
        "photo_label": "Foto Profilo", "border_label": "Spessore Bordo (px)", "preview_label": "Anteprima",
        "main_title": "Generatore CV Professionale", "step1_title": "1. Carica il tuo CV", 
        "upload_help": "Seleziona file PDF", "step2_title": "2. Annuncio di Lavoro", 
        "job_placeholder": "Incolla qui il testo dell'annuncio...",
        "btn_label": "✨ Genera Documenti", "spinner": "Analisi in corso... attendere...",
        "tab1": "CV Grafico", "tab2": "Lettera Presentazione", 
        "down_cv": "Scarica CV (.docx)", "down_let": "Scarica Lettera (.docx)",
        "success": "Documenti creati con successo!", "error": "Errore"
    },
    "en_uk": {
        "sidebar_title": "Profile Settings", "lang_label": "Select Language",
        "photo_label": "Profile Photo", "border_label": "Border Width (px)", "preview_label": "Preview",
        "main_title": "Professional CV Generator", "step1_title": "1. Upload CV",
        "upload_help": "Select PDF file", "step2_title": "2. Job Description",
        "job_placeholder": "Paste job text here...",
        "btn_label": "✨ Generate Documents", "spinner": "Analysis in progress... please wait...",
        "tab1": "Graphic CV", "tab2": "Cover Letter",
        "down_cv": "Download CV (.docx)", "down_let": "Download Letter (.docx)",
        "success": "Documents created successfully!", "error": "Error"
    },
    "en_us": {
        "sidebar_title": "Profile Settings", "lang_label": "Select Language",
        "photo_label": "Profile Photo", "border_label": "Border Width (px)", "preview_label": "Preview",
        "main_title": "Professional Resume Generator", "step1_title": "1. Upload Resume",
        "upload_help": "Select PDF file", "step2_title": "2. Job Description",
        "job_placeholder": "Paste job text here...",
        "btn_label": "✨ Generate Documents", "spinner": "Analysis in progress... please wait...",
        "tab1": "Graphic Resume", "tab2": "Cover Letter",
        "down_cv": "Download Resume (.docx)", "down_let": "Download Letter (.docx)",
        "success": "Documents created successfully!", "error": "Error"
    },
    "de_de": {
        "sidebar_title": "Profileinstellungen", "lang_label": "Sprache auswählen",
        "photo_label": "Profilbild", "border_label": "Rahmenbreite (px)", "preview_label": "Vorschau",
        "main_title": "Professioneller Lebenslauf-Generator", "step1_title": "1. Lebenslauf hochladen",
        "upload_help": "PDF Datei auswählen", "step2_title": "2. Stellenanzeige",
        "job_placeholder": "Hier Text einfügen...",
        "btn_label": "✨ Dokumente erstellen", "spinner": "Analyse läuft... bitte warten...",
        "tab1": "Lebenslauf", "tab2": "Anschreiben",
        "down_cv": "Lebenslauf laden (.docx)", "down_let": "Anschreiben laden (.docx)",
        "success": "Dokumente erfolgreich erstellt!", "error": "Fehler"
    },
    "de_ch": {
        "sidebar_title": "Profileinstellungen", "lang_label": "Sprache auswählen",
        "photo_label": "Profilbild", "border_label": "Rahmenbreite (px)", "preview_label": "Vorschau",
        "main_title": "Professioneller Lebenslauf-Generator", "step1_title": "1. Lebenslauf hochladen",
        "upload_help": "PDF Datei auswählen", "step2_title": "2. Stellenbeschrieb",
        "job_placeholder": "Hier Text einfügen...",
        "btn_label": "✨ Dokumente erstellen", "spinner": "Analyse läuft... bitte warten...",
        "tab1": "Lebenslauf", "tab2": "Begleitschreiben",
        "down_cv": "Lebenslauf laden (.docx)", "down_let": "Begleitschreiben laden (.docx)",
        "success": "Dokumente erfolgreich erstellt!", "error": "Fehler"
    },
    "es": {
        "sidebar_title": "Ajustes de Perfil", "lang_label": "Seleccionar Idioma",
        "photo_label": "Foto de Perfil", "border_label": "Grosor Borde (px)", "preview_label": "Vista Previa",
        "main_title": "Generador de CV Profesional", "step1_title": "1. Subir CV",
        "upload_help": "Seleccionar PDF", "step2_title": "2. Oferta de Trabajo",
        "job_placeholder": "Pegar texto aquí...",
        "btn_label": "✨ Generar Documentos", "spinner": "Análisis en curso...",
        "tab1": "CV Gráfico", "tab2": "Carta de Presentación",
        "down_cv": "Descargar CV (.docx)", "down_let": "Descargar Carta (.docx)",
        "success": "¡Documentos generados!", "error": "Error"
    },
    "pt": {
        "sidebar_title": "Configurações de Perfil", "lang_label": "Selecionar Idioma",
        "photo_label": "Foto de Perfil", "border_label": "Borda da Foto (px)", "preview_label": "Visualização",
        "main_title": "Gerador de Currículo Profissional", "step1_title": "1. Enviar CV",
        "upload_help": "Selecionar PDF", "step2_title": "2. Anúncio de Emprego",
        "job_placeholder": "Colar texto aqui...",
        "btn_label": "✨ Gerar Documentos", "spinner": "Análise em andamento...",
        "tab1": "CV Gráfico", "tab2": "Carta de Apresentação",
        "down_cv": "Baixar CV (.docx)", "down_let": "Baixar Carta (.docx)",
        "success": "Documentos gerados!", "error": "Erro"
    }
}

# Titoli Sezioni Word (Hardcoded)
SECTION_TITLES = {
    "it": {"summary": "PROFILO", "exp": "ESPERIENZA PROFESSIONALE", "edu": "FORMAZIONE", "skills": "COMPETENZE", "lang": "LINGUE"},
    "en_uk": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS", "lang": "LANGUAGES"},
    "en_us": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS", "lang": "LANGUAGES"},
    "de_de": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN", "lang": "SPRACHEN"},
    "de_ch": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN", "lang": "SPRACHEN"},
    "es": {"summary": "PERFIL", "exp": "EXPERIENCIA PROFESIONAL", "edu": "FORMACIÓN", "skills": "HABILIDADES", "lang": "IDIOMAS"},
    "pt": {"summary": "PERFIL", "exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skills": "COMPETÊNCIAS", "lang": "IDIOMAS"}
}

# --- 4. FUNZIONI HELPER ---

def process_image(uploaded_file, border_width_px):
    """Aggiunge il bordo bianco e restituisce PIL Image."""
    if not uploaded_file: return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        if border_width_px > 0:
            img = ImageOps.expand(img, border=int(border_width_px * 2), fill='white')
        return img
    except: return None

def set_cell_bg(cell, color_hex):
    """Sfondo colorato cella Word"""
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_section_header(doc, text):
    """Titolo sezione blu con linea sotto"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(32, 84, 125) # Blu scuro
    
    # Border Bottom
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '20547d')
    pbdr.append(bottom)
    pPr.append(pbdr)

def extract_pdf_text(file):
    try:
        reader = pypdf.PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except: return ""

def get_gemini_response(cv_text, job_desc, lang_code):
    try:
        # CHIAVE API
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        
        # MODELLO
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        lang_prompt = f"Target Language Code: {lang_code}."
        if lang_code == "de_ch":
            lang_prompt += " IMPORTANT: Use Swiss Standard German spelling (NO 'ß', use 'ss')."

        prompt = f"""
        ROLE: You are an expert HR Translator and Resume Writer.
        {lang_prompt}
        
        MANDATORY: 
        1. All content in the output JSON MUST be translated into the target language.
        2. Do NOT use markdown code blocks. Return RAW JSON.
        
        INPUT CV: {cv_text[:25000]}
        JOB DESCRIPTION: {job_desc}
        
        OUTPUT JSON (Strictly this structure):
        {{
            "personal_info": {{ "name": "...", "contact_line": "City | Phone | Email" }},
            "summary_text": "...",
            "experience": [ 
                {{ "role": "...", "company": "...", "dates": "...", "description": "..." }} 
            ],
            "education": [ 
                {{ "degree": "...", "institution": "...", "dates": "..." }} 
            ],
            "skills_list": ["Skill1", "Skill2", "Skill3"],
            "cover_letter_text": "..."
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- 5. CREAZIONE WORD (PIXEL PERFECT LAYOUT) ---

def create_cv_docx(data, pil_image, lang_code):
    doc = Document()
    
    # Margini Pagina
    section = doc.sections[0]
    section.top_margin = Cm(1.27)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    
    # --- HEADER TABLE ---
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    # === MISURE RIGIDE (NO SPAZI VUOTI) ===
    table.columns[0].width = Inches(1.3) # Foto (Stretta)
    table.columns[1].width = Inches(6.0) # Testo (Largo)
    
    # Altezza Riga Banner (2.0 Pollici Esatti)
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    row.height = Inches(2.0)
    
    cell_img = table.cell(0, 0)
    cell_txt = table.cell(0, 1)
    
    # Sfondo Blu
    blue_color = "20547d"
    set_cell_bg(cell_img, blue_color)
    set_cell_bg(cell_txt, blue_color)
    
    # Allineamento Verticale
    cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # --- FOTO ---
    # Pulizia totale paragrafo per centratura
    p_img = cell_img.paragraphs[0]
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(0)
    p_img.paragraph_format.line_spacing = 1.0
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if pil_image:
        try:
            img_byte = io.BytesIO()
            pil_image.save(img_byte, format="PNG")
            img_byte.seek(0)
            
            # Inserimento foto: Altezza 1.5" in Banner 2.0" -> Margine perfetto
            run = p_img.add_run()
            run.add_picture(img_byte, height=Inches(1.5))
        except: pass
        
    # --- TESTO HEADER ---
    p_name = cell_txt.paragraphs[0]
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(0)
    
    run_name = p_name.add_run(data['personal_info']['name'])
    run_name.font.size = Pt(24)
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    run_name.bold = True
    
    p_cont = cell_txt.add_paragraph(data['personal_info']['contact_line'])
    p_cont.paragraph_format.space_before = Pt(6)
    run_cont = p_cont.runs[0]
    run_cont.font.size = Pt(10)
    run_cont.font.color.rgb = RGBColor(230, 230, 230)
    
    doc.add_paragraph().space_after = Pt(12)
    
    # --- BODY ---
    titles = SECTION_TITLES.get(lang_code, SECTION_TITLES['en_us'])
    
    if data.get('summary_text'):
        add_section_header(doc, titles['summary'])
        doc.add_paragraph(data['summary_text'])
    
    if data.get('experience'):
        add_section_header(doc, titles['exp'])
        for exp in data['experience']:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            runner = p.add_run(f"{exp['role']} | {exp['company']}")
            runner.bold = True
            runner.font.color.rgb = RGBColor(32, 84, 125)
            
            p2 = doc.add_paragraph(exp['dates'])
            p2.runs[0].italic = True
            p2.paragraph_format.space_after = Pt(2)
            
            doc.add_paragraph(exp['description']).paragraph_format.space_after = Pt(8)
            
    if data.get('education'):
        add_section_header(doc, titles['edu'])
        for edu in data['education']:
            p = doc.add_paragraph(f"{edu['degree']} - {edu['institution']}")
            p.runs[0].bold = True
            doc.add_paragraph(edu['dates']).runs[0].italic = True
            
    if data.get('skills_list'):
        add_section_header(doc, titles['skills'])
        doc.add_paragraph(", ".join(data['skills_list']))
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_letter_docx(text):
    doc = Document()
    for line in text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 6. MAIN APP LOGIC ---

# Sidebar: Lingua & Foto
with st.sidebar:
    st.title("⚙️ Setup")
    
    # Recupero lingua corrente
    curr_code = st.session_state.lang_code
    curr_label = TRANSLATIONS[curr_code]['lang_label']
    
    # Trova indice per selectbox
    names = list(LANG_MAP.keys())
    codes = list(LANG_MAP.values())
    idx = codes.index(curr_code) if curr_code in codes else 0
    
    sel_name = st.selectbox("Language", names, index=idx, label_visibility="visible")
    new_code = LANG_MAP[sel_name]
    
    # Cambio Lingua -> Rerun
    if new_code != st.session_state.lang_code:
        st.session_state.lang_code = new_code
        st.rerun()
    
    t = TRANSLATIONS[st.session_state.lang_code]
    
    st.markdown("---")
    st.subheader(t['sidebar_title'])
    
    u_photo = st.file_uploader(t['photo_label'], type=['jpg', 'png', 'jpeg'])
    st.write(t['border_label'])
    b_width = st.slider("B_Slider", 0, 50, 10, label_visibility="collapsed")
    
    # Processing Foto immediato
    if u_photo:
        proc_img = process_image(u_photo, b_width)
        if proc_img:
            st.session_state.processed_photo = proc_img
            # Anteprima in sidebar
            buf = io.BytesIO()
            proc_img.save(buf, format="PNG")
            st.image(buf, width=150, caption=t['preview_label'])
    else:
        st.session_state.processed_photo = None

# Main
st.title(f"🚀 {t['main_title']}")

c1, c2 = st.columns(2)
with c1:
    st.subheader(t['step1_title'])
    u_cv = st.file_uploader("CV_Upl", type="pdf", label_visibility="collapsed", help=t['upload_help'])
with c2:
    st.subheader(t['step2_title'])
    job_desc = st.text_area("Job", height=150, label_visibility="collapsed", placeholder=t['job_placeholder'])

if st.button(t['btn_label'], type="primary", use_container_width=True):
    if not u_cv or not job_desc:
        st.warning("Input Missing")
    else:
        with st.spinner(t['spinner']):
            cv_text = extract_pdf_text(u_cv)
            data = get_gemini_response(cv_text, job_desc, st.session_state.lang_code)
            if data:
                st.session_state.generated_data = data
                st.success(t['success'])

# Results
if st.session_state.generated_data:
    d = st.session_state.generated_data
    t1, t2 = st.tabs([t['tab1'], t['tab2']])
    
    with t1:
        st.subheader(d['personal_info']['name'])
        st.caption(d['personal_info']['contact_line'])
        st.write(d['summary_text'])
        st.markdown("---")
        
        docx_cv = create_cv_docx(d, st.session_state.processed_photo, st.session_state.lang_code)
        st.download_button(t['down_cv'], docx_cv, "CV_Optimized.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    with t2:
        st.markdown(d['cover_letter_text'])
        docx_cl = create_letter_docx(d['cover_letter_text'])
        st.download_button(t['down_let'], docx_cl, "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
