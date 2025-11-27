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

# --- 1. COSTANTI E DIZIONARI (DEFINITI SUBITO) ---

LANG_MAP = {
    "Italiano": "it",
    "English (UK)": "en_uk",
    "English (US)": "en_us",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

TRANSLATIONS = {
    "it": {
        "title": "Generatore CV Professionale",
        "sidebar_photo": "Foto Profilo",
        "border_width": "Bordo Foto (px)",
        "upload_cv": "1. Carica CV (PDF)",
        "job_desc": "2. Annuncio di Lavoro",
        "generate_btn": "Genera Documenti",
        "success_msg": "Documenti generati con successo!",
        "error_msg": "Errore durante la generazione:",
        "tab_cv": "CV Grafico",
        "tab_letter": "Lettera Presentazione",
        "download_cv_btn": "Scarica CV (.docx)",
        "download_letter_btn": "Scarica Lettera (.docx)",
        "preview": "Anteprima Foto"
    },
    "en_uk": {
        "title": "Professional CV Generator",
        "sidebar_photo": "Profile Photo",
        "border_width": "Photo Border (px)",
        "upload_cv": "1. Upload CV (PDF)",
        "job_desc": "2. Job Description",
        "generate_btn": "Generate Documents",
        "success_msg": "Documents generated successfully!",
        "error_msg": "Error during generation:",
        "tab_cv": "Graphic CV",
        "tab_letter": "Cover Letter",
        "download_cv_btn": "Download CV (.docx)",
        "download_letter_btn": "Download Letter (.docx)",
        "preview": "Photo Preview"
    },
    "en_us": {
        "title": "Professional Resume Generator",
        "sidebar_photo": "Profile Photo",
        "border_width": "Photo Border (px)",
        "upload_cv": "1. Upload Resume (PDF)",
        "job_desc": "2. Job Description",
        "generate_btn": "Generate Documents",
        "success_msg": "Documents generated successfully!",
        "error_msg": "Error during generation:",
        "tab_cv": "Graphic Resume",
        "tab_letter": "Cover Letter",
        "download_cv_btn": "Download Resume (.docx)",
        "download_letter_btn": "Download Letter (.docx)",
        "preview": "Photo Preview"
    },
    "de_de": {
        "title": "Professioneller Lebenslauf-Generator",
        "sidebar_photo": "Profilbild",
        "border_width": "Rahmenbreite (px)",
        "upload_cv": "1. Lebenslauf hochladen (PDF)",
        "job_desc": "2. Stellenanzeige",
        "generate_btn": "Dokumente erstellen",
        "success_msg": "Dokumente erfolgreich erstellt!",
        "error_msg": "Fehler bei der Erstellung:",
        "tab_cv": "Lebenslauf",
        "tab_letter": "Anschreiben",
        "download_cv_btn": "Lebenslauf laden (.docx)",
        "download_letter_btn": "Anschreiben laden (.docx)",
        "preview": "Vorschau"
    },
    "de_ch": {
        "title": "Professioneller Lebenslauf-Generator (CH)",
        "sidebar_photo": "Profilbild",
        "border_width": "Rahmenbreite (px)",
        "upload_cv": "1. Lebenslauf hochladen (PDF)",
        "job_desc": "2. Stellenbeschrieb",
        "generate_btn": "Dokumente erstellen",
        "success_msg": "Dokumente erfolgreich erstellt!",
        "error_msg": "Fehler bei der Erstellung:",
        "tab_cv": "Lebenslauf",
        "tab_letter": "Begleitschreiben",
        "download_cv_btn": "Lebenslauf laden (.docx)",
        "download_letter_btn": "Begleitschreiben laden (.docx)",
        "preview": "Vorschau"
    },
    "es": {
        "title": "Generador de CV Profesional",
        "sidebar_photo": "Foto de Perfil",
        "border_width": "Borde Foto (px)",
        "upload_cv": "1. Subir CV (PDF)",
        "job_desc": "2. Oferta de Trabajo",
        "generate_btn": "Generar Documentos",
        "success_msg": "Documentos generados con éxito!",
        "error_msg": "Error durante la generación:",
        "tab_cv": "CV Gráfico",
        "tab_letter": "Carta de Presentación",
        "download_cv_btn": "Descargar CV (.docx)",
        "download_letter_btn": "Descargar Carta (.docx)",
        "preview": "Vista Previa"
    },
    "pt": {
        "title": "Gerador de Currículo Profissional",
        "sidebar_photo": "Foto de Perfil",
        "border_width": "Borda da Foto (px)",
        "upload_cv": "1. Enviar CV (PDF)",
        "job_desc": "2. Anúncio de Emprego",
        "generate_btn": "Gerar Documentos",
        "success_msg": "Documentos gerados com sucesso!",
        "error_msg": "Erro durante a geração:",
        "tab_cv": "CV Gráfico",
        "tab_letter": "Carta de Apresentação",
        "download_cv_btn": "Baixar CV (.docx)",
        "download_letter_btn": "Baixar Carta (.docx)",
        "preview": "Visualização"
    }
}

SECTION_TITLES = {
    "it": {"summary": "PROFILO", "exp": "ESPERIENZA PROFESSIONALE", "edu": "FORMAZIONE", "skills": "COMPETENZE"},
    "en_uk": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS"},
    "en_us": {"summary": "PROFILE", "exp": "PROFESSIONAL EXPERIENCE", "edu": "EDUCATION", "skills": "SKILLS"},
    "de_de": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN"},
    "de_ch": {"summary": "PROFIL", "exp": "BERUFSERFAHRUNG", "edu": "AUSBILDUNG", "skills": "KOMPETENZEN"},
    "es": {"summary": "PERFIL", "exp": "EXPERIENCIA PROFESIONAL", "edu": "FORMACIÓN", "skills": "HABILIDADES"},
    "pt": {"summary": "PERFIL", "exp": "EXPERIÊNCIA PROFISSIONAL", "edu": "EDUCAÇÃO", "skills": "COMPETÊNCIAS"}
}

# --- 2. FUNZIONI HELPER ---

def set_cell_bg(cell, color_hex):
    """Colora lo sfondo di una cella Word."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_section_header(doc, text):
    """Titolo sezione blu con linea sotto."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(32, 84, 125) # Blu scuro
    
    # Bordo inferiore (XML Hack)
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

def process_image(uploaded_file, border_width_px):
    """Applica il bordo bianco all'immagine."""
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

def get_image_base64(pil_image):
    """Converte immagine PIL in base64 per HTML."""
    if not pil_image: return None
    try:
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except: return None

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

# --- 3. CREAZIONE WORD (LAYOUT PIXEL PERFECT) ---

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
    table.columns[0].width = Cm(4.5)  # Foto
    table.columns[1].width = Cm(13.0) # Testo
    
    # Altezza Riga Esatta (2.0 pollici)
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
    
    # Foto (1.5 pollici di altezza)
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
            run = p_img.add_run()
            run.add_picture(img_byte, height=Inches(1.5))
        except: pass
        
    # Testo Header
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
    
    # --- CORPO ---
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

# --- 4. MAIN APP ---

st.set_page_config(page_title="Global Career AI", page_icon="👔", layout="wide")

# Init Session State
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None

# Config API Key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 API KEY mancante nei Secrets.")
    st.stop()

# Sidebar: Lingua e Foto
with st.sidebar:
    st.title("⚙️ Setup")
    selected_lang_label = st.selectbox("Lingua / Language", list(LANG_MAP.keys()))
    lang_code = LANG_MAP[selected_lang_label]
    t = TRANSLATIONS[lang_code]
    
    st.markdown("---")
    st.subheader(t['sidebar_photo'])
    u_photo = st.file_uploader(t['sidebar_photo'], type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
    b_width = st.slider(t['border_width'], 0, 20, 8)
    
    processed_img = None
    if u_photo:
        processed_img = process_image(u_photo, b_width)
        if processed_img:
            st.image(processed_img, width=150, caption=t['preview'])

# Main Page
st.title(f"🚀 {t['title']}")

c1, c2 = st.columns(2)
with c1:
    st.subheader(t['upload_cv'])
    u_cv = st.file_uploader(t['upload_cv'], type="pdf", label_visibility="collapsed")
with c2:
    st.subheader(t['job_desc'])
    job_desc = st.text_area(t['job_desc'], height=150, label_visibility="collapsed")

if st.button(t['generate_btn'], type="primary", use_container_width=True):
    if not u_cv or not job_desc:
        st.warning("⚠️ Input mancanti.")
    else:
        with st.spinner("Analisi Gemini 3 Pro..."):
            cv_text = extract_pdf_text(u_cv)
            data = get_gemini_response(cv_text, job_desc, lang_code)
            if data:
                st.session_state.generated_data = data
                st.success(t['success_msg'])

# Output Tabs
if st.session_state.generated_data:
    d = st.session_state.generated_data
    t1, t2 = st.tabs([t['tab_cv'], t['tab_letter']])
    
    with t1:
        st.subheader(d['personal_info']['name'])
        st.caption(d['personal_info']['contact_line'])
        st.write(d['summary_text'])
        st.markdown("---")
        
        docx_cv = create_cv_docx(d, processed_img, lang_code)
        st.download_button(t['download_cv_btn'], docx_cv, "CV_Optimized.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    with t2:
        st.markdown(d['cover_letter_text'])
        docx_cl = create_letter_docx(d['cover_letter_text'])
        st.download_button(t['download_letter_btn'], docx_cl, "Cover_Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
