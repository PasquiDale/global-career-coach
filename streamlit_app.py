import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls, qn
from docx.oxml import parse_xml, OxmlElement
import io
from PIL import Image, ImageOps
import pypdf
from datetime import datetime
import json
import re

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. CSS CUSTOM (FIX MANINA + UI) ---
st.markdown("""
<style>
    /* Forza cursore manina sui menu a tendina */
    div[data-baseweb="select"] > div { cursor: pointer !important; }
    
    /* Forza cursore manina sui bottoni */
    button { cursor: pointer !important; }
    
    /* Spaziatura container principale */
    .main .block-container { padding-top: 2rem; }
    
    /* Stile bottone principale */
    div[data-testid="stFileUploader"] { margin-bottom: 1rem; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; background-color: #20547D; color: white; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None
if 'processed_photo' not in st.session_state:
    st.session_state['processed_photo'] = None

# --- 4. COSTANTI E DIZIONARI ---
LANG_DISPLAY = {
    "Italiano": "it", "English (US)": "en_us", "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de", "Deutsch (Schweiz)": "de_ch",
    "Français": "fr", "Español": "es", "Português": "pt"
}

TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carica CV (PDF)', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'lang_label': 'Lingua'},
    'en_us': {'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'lang_label': 'Language'},
    'en_uk': {'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'lang_label': 'Language'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'lang_label': 'Sprache'},
    'de_de': {'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'lang_label': 'Sprache'},
    'fr': {'sidebar_title': 'Paramètres du Profil', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte ici...', 'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 'success': 'Terminé!', 'error': 'Erreur', 'lang_label': 'Langue'},
    'es': {'sidebar_title': 'Configuración', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'lang_label': 'Idioma'},
    'pt': {'sidebar_title': 'Configurações', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'lang_label': 'Idioma'}
}

SECTION_TITLES = {
    'it': {'experience': 'ESPERIENZA PROFESSIONALE', 'education': 'ISTRUZIONE E FORMAZIONE', 'skills': 'COMPETENZE', 'languages': 'LINGUE', 'interests': 'INTERESSI', 'personal_info': 'DATI PERSONALI', 'profile_summary': 'PROFILO PERSONALE'},
    'de_ch': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE & FÄHIGKEITEN', 'languages': 'SPRACHKENNTNISSE', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'de_de': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHKENNTNISSE', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'fr': {'experience': 'EXPÉRIENCE PROFESSIONNELLE', 'education': 'FORMATION', 'skills': 'COMPÉTENCES', 'languages': 'LANGUES', 'interests': 'CENTRES D\'INTÉRÊT', 'personal_info': 'INFORMATIONS PERSONNELLES', 'profile_summary': 'PROFIL PROFESSIONNEL'},
    'en_us': {'experience': 'PROFESSIONAL EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFESSIONAL SUMMARY'},
    'en_uk': {'experience': 'WORK EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFESSIONAL SUMMARY'},
    'es': {'experience': 'EXPERIENCIA LABORAL', 'education': 'EDUCACIÓN', 'skills': 'HABILIDADES', 'languages': 'IDIOMAS', 'interests': 'INTERESES', 'personal_info': 'DATOS PERSONALES', 'profile_summary': 'PERFIL PROFESIONAL'},
    'pt': {'experience': 'EXPERIÊNCIA PROFISSIONAL', 'education': 'EDUCAÇÃO', 'skills': 'COMPETÊNCIAS', 'languages': 'IDIOMAS', 'interests': 'INTERESSES', 'personal_info': 'DADOS PESSOAIS', 'profile_summary': 'PERFIL PROFISSIONAL'}
}

# --- 5. FUNZIONI HELPER ---

def set_table_background(cell, color_hex):
    """Imposta lo sfondo della cella (XML hacking)."""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def add_bottom_border(paragraph):
    """Aggiunge una linea orizzontale sotto il paragrafo."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'auto')
    pbdr.append(bottom)
    pPr.append(pbdr)

def process_image(uploaded_file, border_width):
    """Elabora la foto per l'anteprima e il documento."""
    if not uploaded_file: return None
    try:
        img = Image.open(uploaded_file).convert("RGB")
        if border_width > 0:
            # Aggiunge il bordo bianco
            img = ImageOps.expand(img, border=border_width, fill='white')
        return img
    except Exception:
        return None

def get_todays_date(lang_code):
    now = datetime.now()
    if lang_code in ['de_ch', 'de_de', 'it', 'fr', 'pt', 'es']:
        return now.strftime("%d.%m.%Y")
    return now.strftime("%B %d, %Y")

def extract_text_from_pdf(pdf_file):
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception:
        return ""

# --- 6. CORE LOGIC: CREAZIONE CV WORD ---

def create_cv_docx(json_data, photo_img, lang_code):
    doc = Document()
    
    # Margini
    section = doc.sections[0]
    section.top_margin = Cm(1.2)
    section.bottom_margin = Cm(1.2)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    # --- HEADER BLU (#20547D) ---
    header_table = doc.add_table(rows=1, cols=2)
    header_table.autofit = False
    header_table.allow_autofit = False
    
    # Dimensioni esatte
    header_table.columns[0].width = Inches(1.2)  # Foto
    header_table.columns[1].width = Inches(6.1)  # Testo
    
    # Altezza fissa header
    row = header_table.rows[0]
    row.height = Inches(2.0)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY

    # Colore Sfondo Blu
    for cell in row.cells:
        set_table_background(cell, "20547D")

    # Cella 1: Foto (Sinistra, Centrata Verticalmente, No Margini)
    cell_photo = header_table.cell(0, 0)
    cell_photo.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if photo_img:
        img_buffer = io.BytesIO()
        photo_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Reset paragrafi per centratura perfetta
        p = cell_photo.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        
        run = p.add_run()
        run.add_picture(img_buffer, width=Inches(1.2))

    # Cella 2: Dati Personali (Centro, Bianco)
    cell_info = header_table.cell(0, 1)
    cell_info.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    pi = json_data.get('personal_info', {})
    
    p_info = cell_info.paragraphs[0]
    p_info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_info.paragraph_format.space_before = Pt(0)
    p_info.paragraph_format.space_after = Pt(0)
    
    # Nome
    name_run = p_info.add_run(f"{pi.get('name', '')}\n")
    name_run.font.name = 'Calibri'
    name_run.font.size = Pt(22)
    name_run.font.color.rgb = RGBColor(255, 255, 255)
    name_run.bold = True
    
    # Contatti
    contact_text = f"{pi.get('address', '')} | {pi.get('phone', '')} | {pi.get('email', '')}\n{pi.get('linkedin', '')}"
    info_run = p_info.add_run(contact_text)
    info_run.font.name = 'Calibri'
    info_run.font.size = Pt(10)
    info_run.font.color.rgb = RGBColor(255, 255, 255)

    doc.add_paragraph().space_after = Pt(12)

    # --- BODY ---
    cv_sections = json_data.get('cv_sections', {})
    titles = SECTION_TITLES.get(lang_code, {})
    
    keys_order = ['profile_summary', 'experience', 'education', 'skills', 'languages', 'interests']
    
    for key in keys_order:
        content = cv_sections.get(key)
        if not content: continue
            
        # Titolo Sezione
        title_text = titles.get(key, key.upper())

        h = doc.add_paragraph()
        add_bottom_border(h)
        run_h = h.add_run(title_text)
        run_h.font.name = 'Calibri'
        run_h.font.size = Pt(12)
        run_h.font.color.rgb = RGBColor(32, 84, 125)
        run_h.bold = True
        h.space_before = Pt(12)
        h.space_after = Pt(6)
        
        # Contenuto
        if isinstance(content, list):
            for item in content:
                p = doc.add_paragraph(str(item), style='List Bullet')
                p.paragraph_format.space_after = Pt(0)
                
                # SPAZIO EXTRA SOLO PER ESPERIENZA ED EDUCAZIONE
                if key in ['experience', 'education']:
                    doc.add_paragraph("") 
        else:
            p = doc.add_paragraph(str(content))
            p.paragraph_format.space_after = Pt(12)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 7. CORE LOGIC: CREAZIONE LETTERA WORD ---

def create_letter_docx(json_data, lang_code, candidate_name):
    doc = Document()
    
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(11)

    ld = json_data.get('letter_data', {})
    pi = json_data.get('personal_info', {})

    # 1. MITTENTE (Alto Sinistra)
    sender_info = f"{pi.get('name', '')}\n{pi.get('address', '')}\n{pi.get('phone', '')}\n{pi.get('email', '')}"
    p_sender = doc.add_paragraph(sender_info)
    p_sender.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_sender.runs[0].font.size = Pt(10)
    p_sender.space_after = Pt(24)

    # 2. DATA (Sinistra)
    real_date = get_todays_date(lang_code)
    p_date = doc.add_paragraph(real_date)
    p_date.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_date.space_after = Pt(12)

    # 3. DESTINATARIO (Sinistra)
    rec = ld.get('recipient_block', '')
    if rec:
        p_rec = doc.add_paragraph(rec)
        p_rec.space_after = Pt(24)

    # 4. OGGETTO
    subj = ld.get('subject_line', '')
    if subj:
        p_subj = doc.add_paragraph()
        run_subj = p_subj.add_run(subj)
        run_subj.bold = True
        run_subj.font.size = Pt(12)
        p_subj.space_after = Pt(12)

    # 5. CORPO
    body = ld.get('body_content', '')
    body = body.replace('**', '').replace('#', '')
    
    for para in body.split('\n'):
        if para.strip():
            p = doc.add_paragraph(para.strip())
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15

    doc.add_paragraph().space_after = Pt(12)

    # 6. FIRMA
    closing = ld.get('closing', 'Freundliche Grüsse')
    if candidate_name:
        closing = closing.replace(candidate_name, "").strip()
        
    p_close = doc.add_paragraph(closing)
    p_close.paragraph_format.keep_with_next = True
    
    # 4 Righe vuote
    for _ in range(4):
        p_s = doc.add_paragraph()
        p_s.paragraph_format.keep_with_next = True
        p_s.paragraph_format.space_after = Pt(0)

    # Nome stampato
    p_name = doc.add_paragraph(candidate_name)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 8. UI PRINCIPALE ---

# Sidebar
with st.sidebar:
    lang_sel = st.selectbox("Language / Lingua", list(LANG_DISPLAY.keys()))
    st.session_state.lang_code = LANG_DISPLAY[lang_sel]
    t = TRANSLATIONS[st.session_state.lang_code]
    
    st.title(t['sidebar_title'])
    st.markdown("---")
    
    # Upload Foto
    uploaded_photo = st.file_uploader(t['photo_label'], type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")
    # Slider esteso a 50px
    border_width = st.slider(t['border_label'], 0, 50, 5)
    
    # Anteprima Foto Processata
    if uploaded_photo:
        processed_img = process_image(uploaded_photo, border_width)
        st.session_state.processed_photo = processed_img
        st.markdown(f"**{t['preview_label']}**")
        if processed_img:
            st.image(processed_img, width=150)
    else:
        st.session_state.processed_photo = None

# Main
st.title(t['main_title'])

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("🚨 API Key mancante nei Secrets!")
    st.stop()

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader(t['step1_title'])
    uploaded_cv = st.file_uploader(t['step1_title'], type=['pdf'], label_visibility="collapsed")
with col2:
    st.subheader(t['step2_title'])
    job_desc = st.text_area(t['step2_title'], height=200, placeholder=t['job_placeholder'], label_visibility="collapsed")

if st.button(t['btn_label'], type="primary"):
    if not uploaded_cv or not job_desc:
        st.warning("Carica CV e Annuncio.")
    else:
        with st.spinner(t['spinner_msg']):
            try:
                cv_text = extract_text_from_pdf(uploaded_cv)
                
                # --- CHIAMATA AI (NO TOOLS) ---
                model = genai.GenerativeModel("models/gemini-3-pro-preview")
                
                prompt = f"""
                Act as an expert HR Resume Writer.
                Target Language: {lang_sel} ({st.session_state.lang_code}).
                
                INPUT:
                1. RESUME TEXT: {cv_text[:30000]}
                2. JOB DESCRIPTION: {job_desc}
                
                TASK:
                Generate a structured JSON.
                
                MANDATORY JSON STRUCTURE:
                {{
                    "personal_info": {{ "name": "...", "address": "...", "phone": "...", "email": "...", "linkedin": "..." }},
                    "cv_sections": {{
                        "profile_summary": "Short summary...",
                        "experience": ["Role | Company | Date ... description...", "Role 2..."],
                        "education": ["Degree..."],
                        "skills": ["Skill 1", "Skill 2..."],
                        "languages": ["Lang 1..."],
                        "interests": ["Interest 1..."]
                    }},
                    "letter_data": {{
                        "recipient_block": "Company Name\\nAddress",
                        "subject_line": "Subject...",
                        "body_content": "Letter body...",
                        "closing": "Greeting ONLY (e.g. Freundliche Grüsse)"
                    }}
                }}
                
                RULES:
                - Output strict JSON.
                - NO candidate name in 'closing'.
                - 'experience' MUST be a list of strings.
                """
                
                response = model.generate_content(prompt)
                
                json_str = response.text.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:-3]
                
                data = json.loads(json_str)
                st.session_state.generated_data = data
                st.success(t['success'])
                
            except Exception as e:
                st.error(f"{t['error']}: {str(e)}")

if st.session_state.generated_data:
    data = st.session_state.generated_data
    tabs = st.tabs([t['tab_cv'], t['tab_letter']])
    
    with tabs[0]:
        docx_cv = create_cv_docx(data, st.session_state.processed_photo, st.session_state.lang_code)
        st.download_button(
            label=t['down_cv'],
            data=docx_cv,
            file_name=f"CV_Optimized.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.json(data['cv_sections'])

    with tabs[1]:
        candidate_name = data['personal_info'].get('name', 'Candidate')
        docx_let = create_letter_docx(data, st.session_state.lang_code, candidate_name)
        st.download_button(
            label=t['down_let'],
            data=docx_let,
            file_name=f"Cover_Letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.write(data['letter_data'])
