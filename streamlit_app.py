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

# CSS per pulizia
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    .stFileUploader label {font-size: 90%;}
    /* Bordo sottile grigio per l'anteprima foto nella sidebar per staccare dal bianco */
    .stImage {border: 1px solid #ddd; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# Session State
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None

# --- 2. DIZIONARI LINGUA & TITOLI ---

LANG_CODES = {
    "Italiano": "it",
    "English (UK)": "en_uk",
    "English (US)": "en_us",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

UI_TEXT = {
    "it": {"title": "Generatore CV Professionale", "ph_lbl": "Foto Profilo", "bord_lbl": "Spessore Bordo (px)", "cv_lbl": "Carica CV (PDF)", "job_lbl": "Annuncio di Lavoro", "btn": "Genera Documenti", "dl_cv": "Scarica CV (.docx)", "dl_cl": "Scarica Lettera (.docx)"},
    "en_uk": {"title": "Professional CV Generator", "ph_lbl": "Profile Photo", "bord_lbl": "Border Width (px)", "cv_lbl": "Upload CV (PDF)", "job_lbl": "Job Description", "btn": "Generate Documents", "dl_cv": "Download CV (.docx)", "dl_cl": "Download Letter (.docx)"},
    "en_us": {"title": "Professional Resume Generator", "ph_lbl": "Profile Photo", "bord_lbl": "Border Width (px)", "cv_lbl": "Upload Resume (PDF)", "job_lbl": "Job Description", "btn": "Generate Documents", "dl_cv": "Download Resume (.docx)", "dl_cl": "Download Letter (.docx)"},
    "de_de": {"title": "Professioneller Lebenslauf-Generator", "ph_lbl": "Profilbild", "bord_lbl": "Rahmenbreite (px)", "cv_lbl": "Lebenslauf hochladen (PDF)", "job_lbl": "Stellenanzeige", "btn": "Dokumente erstellen", "dl_cv": "Lebenslauf laden (.docx)", "dl_cl": "Anschreiben laden (.docx)"},
    "de_ch": {"title": "Professioneller Lebenslauf-Generator", "ph_lbl": "Profilbild", "bord_lbl": "Rahmenbreite (px)", "cv_lbl": "Lebenslauf hochladen (PDF)", "job_lbl": "Stellenbeschrieb", "btn": "Dokumente erstellen", "dl_cv": "Lebenslauf laden (.docx)", "dl_cl": "Begleitschreiben laden (.docx)"},
    "es": {"title": "Generador de CV Profesional", "ph_lbl": "Foto de Perfil", "bord_lbl": "Grosor Borde (px)", "cv_lbl": "Subir CV (PDF)", "job_lbl": "Oferta de Trabajo", "btn": "Generar Documentos", "dl_cv": "Descargar CV (.docx)", "dl_cl": "Descargar Carta (.docx)"},
    "pt": {"title": "Gerador de Currículo Profissional", "ph_lbl": "Foto de Perfil", "bord_lbl": "Borda da Foto (px)", "cv_lbl": "Enviar CV (PDF)", "job_lbl": "Anúncio de Emprego", "btn": "Gerar Documentos", "dl_cv": "Baixar CV (.docx)", "dl_cl": "Baixar Carta (.docx)"}
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

def process_image_with_border(uploaded_file, border_width_px):
    """
    Legge l'immagine, aggiunge fisicamente il bordo bianco e restituisce l'oggetto PIL.
    """
    if not uploaded_file: return None
    try:
        # Resetta puntatore se necessario
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        
        # Converte in RGB se necessario (es. PNG trasparente) per salvare come JPG/PNG standard
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # Aggiunge bordo bianco usando ImageOps
        if border_width_px > 0:
            img = ImageOps.expand(img, border=border_width_px, fill='white')
            
        return img
    except Exception as e:
        print(f"Errore immagine: {e}")
        return None

def pil_image_to_base64(pil_image):
    """Converte un oggetto PIL processato in base64 per HTML."""
    if not pil_image: return None
    buffered = io.BytesIO()
    pil_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

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

# --- 5. LOGICA AI ---

def get_ai_data(cv_text, job_desc, lang_code):
    try:
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        lang_prompt = f"Target Language: {lang_code}."
        if lang_code == "de_ch":
            lang_prompt += " IMPORTANT: Use Swiss Standard German spelling (use 'ss' instead of 'ß')."

        prompt = f"""
        ROLE: You are an expert HR Translator and Resume Writer.
        {lang_prompt}
        
        MANDATORY: All content in the output JSON (descriptions, roles, skills, summary) MUST be translated into the selected language. 
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

def create_cv_docx(data, pil_photo, lang_code):
    doc = Document()
    
    # Margini Pagina (Stretti)
    section = doc.sections[0]
    section.top_margin = Cm(1.27)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    
    # --- HEADER TABLE ---
    # Creiamo una tabella per il banner blu
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    # Larghezza colonne
    table.columns[0].width = Cm(4.5)  # Colonna Foto
    table.columns[1].width = Cm(13.0) # Colonna Testo
    
    # === ALTEZZA RIGA ESATTA (FIX CRITICO) ===
    # Banner: 2.0 Pollici (5.08 cm)
    # Foto:   1.5 Pollici (3.81 cm)
    # Margine risultante: 0.25" sopra e 0.25" sotto -> Look compatto e professionale
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
    
    if pil_photo:
        try:
            # Salviamo l'immagine processata (che ha già il bordo) in un buffer per Word
            img_byte = io.BytesIO()
            pil_photo.save(img_byte, format="PNG")
            img_byte.seek(0)
            
            # Inserimento foto a 1.5 pollici (con Aspect Ratio bloccato sulla larghezza automatica)
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
    titles = SECTION_TITLES[lang_code]
    
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
            runner.font.color.rgb = RGBColor(32, 84, 125) # Blu
            
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

# --- 7. UI ---

# Sidebar
with st.sidebar:
    st.title("⚙️ Setup")
    selected_lang_name = st.selectbox("Lingua / Language", list(LANG_CODES.keys()))
    lang_code = LANG_CODES[selected_lang_name]
    ui = UI_TEXT[lang_code]
    
    st.markdown("---")
    st.subheader(ui["ph_lbl"])
    
    # Upload Foto
    u_photo = st.file_uploader("Foto", type=['jpg','png','jpeg'], label_visibility="collapsed")
    b_width = st.slider(ui["bord_lbl"], 0, 20, 8)
    
    processed_pil_photo = None
    
    # Logica Anteprima Foto (Processata subito)
    if u_photo:
        processed_pil_photo = process_image_with_border(u_photo, b_width)
        if processed_pil_photo:
            st.image(processed_pil_photo, width=150, caption="Anteprima Bordo")

# Main
st.title(f"🚀 {ui['title']}")

c1, c2 = st.columns(2)
with c1:
    u_cv = st.file_uploader(ui["cv_lbl"], type="pdf")
with c2:
    job_desc = st.text_area(ui["job_lbl"], height=100)

if st.button(ui["btn"], type="primary", use_container_width=True):
    if not u_cv or not job_desc:
        st.warning("Input mancanti.")
    else:
        with st.spinner("Analisi Gemini 3 Pro..."):
            cv_text = extract_pdf_text(u_cv)
            data = get_ai_data(cv_text, job_desc, lang_code)
            if data:
                st.session_state.generated_data = data
                st.success("OK!")

# Output
if st.session_state.generated_data:
    d = st.session_state.generated_data
    t1, t2 = st.tabs(["CV", "Lettera"])
    
    with t1:
        # Preview HTML (Usa l'immagine processata se c'è)
        if processed_pil_photo:
            b64 = pil_image_to_base64(processed_pil_photo)
            st.image(f"data:image/png;base64,{b64}", width=100)
        
        st.subheader(d['personal_info']['name'])
        st.write(d['summary_text'])
        st.divider()
        
        # Passiamo l'oggetto PIL processato alla funzione Word
        docx = create_cv_docx(d, processed_pil_photo, b_width, lang_code)
        st.download_button(ui["dl_cv"], docx, "CV.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    with t2:
        st.markdown(d['cover_letter_text'])
        docx_l = create_letter_docx(d['cover_letter_text'])
        st.download_button(ui["dl_cl"], docx_l, "Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
