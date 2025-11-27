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

# --- 1. SETUP ---
st.set_page_config(page_title="Global Career AI", page_icon="👔", layout="wide")

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

# --- 2. DIZIONARI LINGUA & TRADUZIONI (DEFINITI SUBITO PER EVITARE ERRORI) ---

LANG_MAP = {
    "Italiano": "it",
    "English (UK)": "en_uk",
    "English (US)": "en_us",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

# Testi Interfaccia
TRANSLATIONS = {
    "it": {"sidebar_title": "Impostazioni Profilo", "upload_photo": "Carica Foto", "border_width": "Spessore Bordo", "main_title": "AI Career Assistant", "upload_cv": "1. Carica CV (PDF)", "job_desc": "2. Annuncio di Lavoro", "generate_btn": "Genera Documenti", "tab_cv": "CV Generato", "tab_letter": "Lettera Presentazione", "download_cv": "Scarica CV (.docx)", "download_letter": "Scarica Lettera (.docx)", "success": "Fatto!", "error": "Errore:"},
    "en_uk": {"sidebar_title": "Profile Settings", "upload_photo": "Upload Photo", "border_width": "Border Width", "main_title": "AI Career Assistant", "upload_cv": "1. Upload CV (PDF)", "job_desc": "2. Job Description", "generate_btn": "Generate Documents", "tab_cv": "Generated CV", "tab_letter": "Cover Letter", "download_cv": "Download CV (.docx)", "download_letter": "Download Letter (.docx)", "success": "Done!", "error": "Error:"},
    "en_us": {"sidebar_title": "Profile Settings", "upload_photo": "Upload Photo", "border_width": "Border Width", "main_title": "AI Career Assistant", "upload_cv": "1. Upload Resume (PDF)", "job_desc": "2. Job Description", "generate_btn": "Generate Documents", "tab_cv": "Generated Resume", "tab_letter": "Cover Letter", "download_cv": "Download Resume (.docx)", "download_letter": "Download Letter (.docx)", "success": "Done!", "error": "Error:"},
    "de_de": {"sidebar_title": "Profileinstellungen", "upload_photo": "Foto hochladen", "border_width": "Rahmenbreite", "main_title": "KI Karriere-Assistent", "upload_cv": "1. Lebenslauf (PDF)", "job_desc": "2. Stellenanzeige", "generate_btn": "Dokumente erstellen", "tab_cv": "Lebenslauf", "tab_letter": "Anschreiben", "download_cv": "Lebenslauf laden (.docx)", "download_letter": "Anschreiben laden (.docx)", "success": "Fertig!", "error": "Fehler:"},
    "de_ch": {"sidebar_title": "Profileinstellungen", "upload_photo": "Foto hochladen", "border_width": "Rahmenbreite", "main_title": "KI Karriere-Assistent", "upload_cv": "1. Lebenslauf (PDF)", "job_desc": "2. Stellenbeschrieb", "generate_btn": "Dokumente erstellen", "tab_cv": "Lebenslauf", "tab_letter": "Begleitschreiben", "download_cv": "Lebenslauf laden (.docx)", "download_letter": "Begleitschreiben laden (.docx)", "success": "Fertig!", "error": "Fehler:"},
    "es": {"sidebar_title": "Ajustes de Perfil", "upload_photo": "Subir Foto", "border_width": "Grosor Borde", "main_title": "Asistente de Carrera IA", "upload_cv": "1. Subir CV (PDF)", "job_desc": "2. Oferta de Trabajo", "generate_btn": "Generar Documentos", "tab_cv": "CV Generado", "tab_letter": "Carta de Presentación", "download_cv": "Descargar CV (.docx)", "download_letter": "Descargar Carta (.docx)", "success": "¡Hecho!", "error": "Error:"},
    "pt": {"sidebar_title": "Configurações de Perfil", "upload_photo": "Carregar Foto", "border_width": "Borda da Foto", "main_title": "Assistente de Carreira IA", "upload_cv": "1. Enviar CV (PDF)", "job_desc": "2. Anúncio de Emprego", "generate_btn": "Gerar Documentos", "tab_cv": "CV Gerado", "tab_letter": "Carta de Apresentação", "download_cv": "Baixar CV (.docx)", "download_letter": "Baixar Carta (.docx)", "success": "Pronto!", "error": "Erro:"}
}

# Titoli Sezioni Word (Hardcoded per sicurezza linguistica)
SECTION_TITLES = {
    "it": {"summary": "PROFILO", "exp": "ESPERIENZA PROFESSIONALE", "edu": "FORMAZIONE", "skills": "COMPETENZE"},
    "en_uk": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS"},
    "en_us": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS"},
    "de_de": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN"},
    "de_ch": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN"},
    "es": {"summary": "PERFIL", "exp": "EXPERIENCIA PROFESIONAL", "edu": "FORMACIÓN", "skills": "HABILIDADES"},
    "pt": {"summary": "PERFIL", "exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skills": "COMPETÊNCIAS"}
}

# --- 3. API CONFIG ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 API KEY mancante. Aggiungila nei Secrets.")
    st.stop()

# --- 4. FUNZIONI HELPER ---

def process_image(uploaded_file, border_width_px):
    """Aggiunge il bordo bianco all'immagine e restituisce oggetto PIL."""
    if not uploaded_file: return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Bordo (moltiplicato per 2 per alta risoluzione)
        if border_width_px > 0:
            img = ImageOps.expand(img, border=int(border_width_px * 2), fill='white')
        return img
    except Exception:
        return None

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
    
    # Border Bottom (XML hack)
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
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        lang_prompt = f"Target Language Code: {lang_code}."
        if lang_code == "de_ch":
            lang_prompt += " IMPORTANT: Use Swiss Standard German (no 'ß', use 'ss')."

        prompt = f"""
        ROLE: You are an expert HR Resume Writer.
        {lang_prompt}
        
        MANDATORY: 
        1. All content in the output JSON MUST be translated into the target language.
        2. Do NOT use markdown code blocks. Just raw JSON.
        
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

# --- 5. CREAZIONE WORD (LAYOUT PIXEL PERFECT) ---

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
    
    # Larghezza colonne
    table.columns[0].width = Cm(4.5)  # Foto
    table.columns[1].width = Cm(13.0) # Testo
    
    # === ALTEZZA RIGA ESATTA ===
    # Banner: 2.0 Pollici. Foto: 1.5 Pollici.
    # Risultato: Foto perfettamente centrata e avvolta dal blu.
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    row.height = Inches(2.0)
    
    cell_img = table.cell(0, 0)
    cell_txt = table.cell(0, 1)
    
    # Sfondo Blu (#20547d)
    blue_color = "20547d"
    set_cell_bg(cell_img, blue_color)
    set_cell_bg(cell_txt, blue_color)
    
    # === ALLINEAMENTO VERTICALE ===
    cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # --- FOTO ---
    # Pulizia totale paragrafo per centratura matematica
    p_img = cell_img.paragraphs[0]
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(0)
    p_img.paragraph_format.line_spacing = 1.0
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if pil_image:
        try:
            # Salvataggio in memoria buffer per Word
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

# --- 6. LOGICA PRINCIPALE (MAIN) ---

# Sidebar: Lingua
with st.sidebar:
    selected_lang_label = st.selectbox("Lingua / Language", list(LANG_MAP.keys()))
    lang_code = LANG_MAP[selected_lang_label]
    txt = TRANSLATIONS[lang_code]
    
    st.title(txt['sidebar_title'])
    
    # Foto e Slider
    uploaded_photo = st.file_uploader(txt['upload_photo'], type=['jpg', 'png', 'jpeg'])
    border_val = st.slider(txt['border_width'], 0, 20, 8)
    
    processed_img = None
    if uploaded_photo:
        processed_img = process_image(uploaded_photo, border_val)
        if processed_img:
            st.image(processed_img, width=150, caption="Preview")

# Main Page
st.title(f"🚀 {txt['main_title']}")

c1, c2 = st.columns(2)
with c1:
    uploaded_cv = st.file_uploader(txt['upload_cv'], type="pdf")
with c2:
    job_desc = st.text_area(txt['job_desc'], height=100)

if st.button(txt['generate_btn'], type="primary", use_container_width=True):
    if not uploaded_cv or not job_desc:
        st.warning("Input mancanti.")
    else:
        with st.spinner("Gemini 3 Pro..."):
            cv_text = extract_pdf_text(uploaded_cv)
            data = get_gemini_response(cv_text, job_desc, lang_code)
            
            if data:
                st.session_state.generated_data = data
                st.success(txt['success'])

# Output Tabs
if st.session_state.generated_data:
    d = st.session_state.generated_data
    t1, t2 = st.tabs([txt['tab_cv'], txt['tab_letter']])
    
    with t1:
        st.subheader(d['personal_info']['name'])
        st.write(d['summary_text'])
        
        # Qui passiamo l'immagine processata
        docx_cv = create_cv_docx(d, processed_img, lang_code)
        st.download_button(txt['download_cv'], docx_cv, "CV_Optimized.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    with t2:
        st.markdown(d['cover_letter_text'])
        docx_cl = create_letter_docx(d['cover_letter_text'])
        st.download_button(txt['download_letter'], docx_cl, "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
