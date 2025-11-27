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

# --- 1. SETUP (SIDEBAR EXPANDED FIX) ---
st.set_page_config(
    page_title="Global Career AI", 
    page_icon="👔", 
    layout="wide",
    initial_sidebar_state="expanded" # FIX: La barra laterale parte sempre aperta
)

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

# Session State Init
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None
if "lang_code" not in st.session_state:
    st.session_state.lang_code = "it"

# --- 2. DIZIONARI LINGUA & TRADUZIONI ---

LANG_MAP = {
    "Italiano": "it",
    "English (UK)": "en_uk",
    "English (US)": "en_us",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

# Traduzioni Complete (STEALTH MODE - No "AI" in tedesco)
TRANSLATIONS = {
    "it": {
        "language_label": "Seleziona Lingua", "sidebar_title": "Impostazioni Profilo", "ph_lbl": "Foto Profilo", 
        "bord_lbl": "Spessore Bordo (px)", "preview_photo": "Anteprima", "main_title": "Generatore CV Professionale",
        "upload_cv": "1. Carica il tuo CV (PDF)", "job_lbl": "2. Incolla l'Annuncio di Lavoro", 
        "btn": "✨ Genera Documenti", "spinner_msg": "Analisi in corso... attendere...", 
        "tab_cv": "CV Grafico", "tab_letter": "Lettera Presentazione", 
        "download_cv": "Scarica CV (.docx)", "download_letter": "Scarica Lettera (.docx)",
        "success": "Documenti creati con successo!", "error": "Errore", "warn_msg": "⚠️ Carica CV e Annuncio."
    },
    "en_uk": {
        "language_label": "Select Language", "sidebar_title": "Profile Settings", "ph_lbl": "Profile Photo", 
        "bord_lbl": "Border Width (px)", "preview_photo": "Preview", "main_title": "Professional CV Generator",
        "upload_cv": "1. Upload CV (PDF)", "job_lbl": "2. Paste Job Description", 
        "btn": "✨ Generate Documents", "spinner_msg": "Analysis in progress... please wait...", 
        "tab_cv": "Graphic CV", "tab_letter": "Cover Letter", 
        "download_cv": "Download CV (.docx)", "download_letter": "Download Letter (.docx)",
        "success": "Documents created successfully!", "error": "Error", "warn_msg": "⚠️ Please upload CV and Job Ad."
    },
    "en_us": {
        "language_label": "Select Language", "sidebar_title": "Profile Settings", "ph_lbl": "Profile Photo", 
        "bord_lbl": "Border Width (px)", "preview_photo": "Preview", "main_title": "Professional Resume Generator",
        "upload_cv": "1. Upload Resume (PDF)", "job_lbl": "2. Paste Job Description", 
        "btn": "✨ Generate Documents", "spinner_msg": "Analysis in progress... please wait...", 
        "tab_cv": "Graphic Resume", "tab_letter": "Cover Letter", 
        "download_cv": "Download Resume (.docx)", "download_letter": "Download Letter (.docx)",
        "success": "Documents created successfully!", "error": "Error", "warn_msg": "⚠️ Please upload Resume and Job Ad."
    },
    "de_de": {
        "language_label": "Sprache auswählen", "sidebar_title": "Profileinstellungen", "ph_lbl": "Profilbild", 
        "bord_lbl": "Rahmenbreite (px)", "preview_photo": "Vorschau", "main_title": "Professioneller Lebenslauf-Generator",
        "upload_cv": "1. Lebenslauf hochladen (PDF)", "job_lbl": "2. Stellenanzeige einfügen", 
        "btn": "✨ Dokumente erstellen", "spinner_msg": "Analyse läuft... bitte warten...", 
        "tab_cv": "Lebenslauf", "tab_letter": "Anschreiben", 
        "download_cv": "Lebenslauf laden (.docx)", "download_letter": "Anschreiben laden (.docx)",
        "success": "Dokumente erfolgreich erstellt!", "error": "Fehler", "warn_msg": "⚠️ Bitte CV und Anzeige hochladen."
    },
    "de_ch": {
        "language_label": "Sprache auswählen", "sidebar_title": "Profileinstellungen", "ph_lbl": "Profilbild", 
        "bord_lbl": "Rahmenbreite (px)", "preview_photo": "Vorschau", "main_title": "Professioneller Lebenslauf-Generator",
        "upload_cv": "1. Lebenslauf hochladen (PDF)", "job_lbl": "2. Stellenbeschrieb einfügen", 
        "btn": "✨ Dokumente erstellen", "spinner_msg": "Analyse läuft... bitte warten...", 
        "tab_cv": "Lebenslauf", "tab_letter": "Begleitschreiben", 
        "download_cv": "Lebenslauf laden (.docx)", "download_letter": "Begleitschreiben laden (.docx)",
        "success": "Dokumente erfolgreich erstellt!", "error": "Fehler", "warn_msg": "⚠️ Bitte CV und Stellenbeschrieb hochladen."
    },
    "es": {
        "language_label": "Seleccionar Idioma", "sidebar_title": "Ajustes de Perfil", "ph_lbl": "Foto de Perfil", 
        "bord_lbl": "Grosor Borde (px)", "preview_photo": "Vista Previa", "main_title": "Generador de CV Profesional",
        "upload_cv": "1. Subir CV (PDF)", "job_lbl": "2. Pegar Oferta de Trabajo", 
        "btn": "✨ Generar Documentos", "spinner_msg": "Análisis en curso...", 
        "tab_cv": "CV Gráfico", "tab_letter": "Carta de Presentación", 
        "download_cv": "Descargar CV (.docx)", "download_letter": "Descargar Carta (.docx)",
        "success": "¡Documentos generados!", "error": "Error", "warn_msg": "⚠️ Sube CV y Oferta."
    },
    "pt": {
        "language_label": "Selecionar Idioma", "sidebar_title": "Configurações de Perfil", "ph_lbl": "Foto de Perfil", 
        "bord_lbl": "Borda da Foto (px)", "preview_photo": "Visualização", "main_title": "Gerador de Currículo Profissional",
        "upload_cv": "1. Enviar CV (PDF)", "job_lbl": "2. Colar Anúncio de Emprego", 
        "btn": "✨ Gerar Documentos", "spinner_msg": "Análise em andamento...", 
        "tab_cv": "CV Gráfico", "tab_letter": "Carta de Apresentação", 
        "download_cv": "Baixar CV (.docx)", "download_letter": "Baixar Carta (.docx)",
        "success": "Documentos gerados!", "error": "Erro", "warn_msg": "⚠️ Envie CV e Anúncio."
    }
}

SECTION_TITLES = {
    "it": {"summary": "PROFILO", "exp": "ESPERIENZA PROFESSIONALE", "edu": "FORMAZIONE", "skills": "COMPETENZE", "lang": "LINGUE"},
    "en_uk": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS", "lang": "LANGUAGES"},
    "en_us": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS", "lang": "LANGUAGES"},
    "de_de": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN", "lang": "SPRACHEN"},
    "de_ch": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN", "lang": "SPRACHEN"},
    "es": {"summary": "PERFIL", "exp": "EXPERIENCIA PROFESIONAL", "edu": "FORMACIÓN", "skills": "HABILIDADES", "lang": "IDIOMAS"},
    "pt": {"summary": "PERFIL", "exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skills": "COMPETÊNCIAS", "lang": "IDIOMAS"}
}

# --- 3. API CONFIG ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 API KEY mancante.")
    st.stop()

# --- 4. FUNZIONI HELPER ---

def process_image(uploaded_file, border_width_px):
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
    """Sfondo colorato cella Word via XML"""
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
    run.font.color.rgb = RGBColor(32, 84, 125) # Blu #20547d
    
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

def get_image_base64(uploaded_file, border_width):
    if not uploaded_file: return None
    try:
        image = Image.open(uploaded_file)
        if border_width > 0:
            image = ImageOps.expand(image, border=border_width, fill='white')
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except: return None

# --- 5. LOGICA AI ---

def get_gemini_response(cv_text, job_desc, lang_code):
    try:
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        lang_prompt = f"Target Language Code: {lang_code}."
        if lang_code == "de_ch":
            lang_prompt += " IMPORTANT: Use Swiss Standard German spelling (use 'ss' instead of 'ß')."

        prompt = f"""
        ROLE: You are an expert HR Translator and Resume Writer.
        {lang_prompt}
        
        MANDATORY: 
        1. All content in the output JSON (descriptions, roles, skills, summary) MUST be translated into the selected language. 
        Do not leave any sentence in the original language of the PDF.
        
        INPUT CV: {cv_text[:25000]}
        JOB DESCRIPTION: {job_desc}
        
        TASK:
        1. Extract personal info accurately.
        2. Rewrite CV content to match the job description, fully translated.
        3. Write a Cover Letter in the selected language.
        
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

# --- 6. WORD GENERATION (PIXEL PERFECT LAYOUT) ---

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
    
    # === COLONNE OTTIMIZZATE (FIX SPAZI) ===
    table.columns[0].width = Inches(1.4)  # Foto (Più stretta)
    table.columns[1].width = Inches(5.8)  # Testo (Molto largo)
    
    # Altezza Riga Esatta
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
            
            # Inserimento foto a 1.5 pollici
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

# --- 7. MAIN LOGIC (UI) ---

# Sidebar: Lingua
with st.sidebar:
    st.title("⚙️ Setup")
    
    current_lang_code = st.session_state.lang_code
    current_label = TRANSLATIONS[current_lang_code]['language_label']
    
    lang_keys = list(LANG_MAP.keys())
    default_idx = 0
    for i, key in enumerate(lang_keys):
        if LANG_MAP[key] == current_lang_code:
            default_idx = i
            break
            
    selected_lang_name = st.selectbox(current_label, lang_keys, index=default_idx)
    
    new_lang_code = LANG_MAP[selected_lang_name]
    if new_lang_code != st.session_state.lang_code:
        st.session_state.lang_code = new_lang_code
        st.rerun()
    
    t = TRANSLATIONS[st.session_state.lang_code]
    
    st.markdown("---")
    st.subheader(t['sidebar_title'])
    
    u_photo = st.file_uploader(t['ph_lbl'], type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
    
    st.write(t['bord_lbl'])
    # Slider a 50px
    b_width = st.slider("Slider_Border", 0, 50, 10, label_visibility="collapsed")
    
    processed_img = None
    if u_photo:
        processed_img = process_image(u_photo, b_width)
        if processed_img:
            buf = io.BytesIO()
            processed_img.save(buf, format="PNG")
            st.image(buf, width=150, caption=t['preview_photo'])

# Main Page
st.title(f"🚀 {t['main_title']}")

c1, c2 = st.columns(2)
with c1:
    st.subheader(t['upload_cv'])
    u_cv = st.file_uploader("Upload_CV", type="pdf", label_visibility="collapsed")
with c2:
    st.subheader(t['job_lbl'])
    job_desc = st.text_area("Job_Desc", height=150, label_visibility="collapsed")

if st.button(t['btn'], type="primary", use_container_width=True):
    if not u_cv or not job_desc:
        st.warning(t['warn_msg'])
    else:
        with st.spinner(t['spinner_msg']):
            cv_text = extract_pdf_text(u_cv)
            data = get_gemini_response(cv_text, job_desc, st.session_state.lang_code)
            
            if data:
                st.session_state.generated_data = data
                st.success(t['success'])

# Output Tabs
if st.session_state.generated_data:
    d = st.session_state.generated_data
    t1, t2 = st.tabs([t['tab_cv'], t['tab_letter']])
    
    with t1:
        st.subheader(d['personal_info']['name'])
        st.caption(d['personal_info']['contact_line'])
        st.write(d['summary_text'])
        st.markdown("---")
        
        docx_cv = create_cv_docx(d, processed_img, st.session_state.lang_code)
        st.download_button(t['dl_cv'], docx_cv, "CV_Optimized.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    with t2:
        st.markdown(d['cover_letter_text'])
        docx_cl = create_letter_docx(d['cover_letter_text'])
        st.download_button(t['dl_cl'], docx_cl, "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
