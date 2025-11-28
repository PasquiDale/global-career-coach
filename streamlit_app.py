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
import json
import datetime

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS INJECTION ---
st.markdown("""
    <style>
    div[data-baseweb="select"] > div { cursor: pointer !important; }
    button { cursor: pointer !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state: st.session_state.lang_code = 'it'
if 'generated_data' not in st.session_state: st.session_state.generated_data = None
if 'processed_photo' not in st.session_state: st.session_state.processed_photo = None

# --- 4. COSTANTI E DIZIONARI ---

LANG_DISPLAY = {
    "Italiano": "it", "English (US)": "en_us", "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de", "Deutsch (Schweiz)": "de_ch",
    "Français": "fr", "Español": "es", "Português": "pt"
}

TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carica CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'missing_key': 'Chiave API mancante'},
    'en_us': {'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'missing_key': 'Missing API Key'},
    'de_de': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt'},
    'fr': {'sidebar_title': 'Paramètres du Profil', 'lang_label': 'Langue', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 'upload_help': 'Déposez le fichier ici', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte de l\'offre ici...', 'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 'success': 'Terminé!', 'error': 'Erreur', 'missing_key': 'Clé API manquante'},
    'es': {'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'missing_key': 'Falta clave API'},
    'pt': {'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'missing_key': 'Chave API ausente'},
    'en_uk': {'sidebar_title': 'Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'missing_key': 'Missing API Key'}
}

SECTION_TITLES = {
    'it': {'experience': 'ESPERIENZA PROFESSIONALE', 'education': 'ISTRUZIONE E FORMAZIONE', 'skills': 'COMPETENZE', 'personal_info': 'DATI PERSONALI', 'profile_summary': 'PROFILO PERSONALE'},
    'de_ch': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE & FÄHIGKEITEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'de_de': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'fr': {'experience': 'EXPÉRIENCE PROFESSIONNELLE', 'education': 'FORMATION', 'skills': 'COMPÉTENCES', 'personal_info': 'INFORMATIONS PERSONNELLES', 'profile_summary': 'PROFIL PROFESSIONNEL'},
    'en_us': {'experience': 'PROFESSIONAL EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFESSIONAL PROFILE'},
    'en_uk': {'experience': 'WORK EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFESSIONAL PROFILE'},
    'es': {'experience': 'EXPERIENCIA LABORAL', 'education': 'EDUCACIÓN', 'skills': 'HABILIDADES', 'personal_info': 'DATOS PERSONALES', 'profile_summary': 'PERFIL PROFESIONAL'},
    'pt': {'experience': 'EXPERIÊNCIA PROFISSIONAL', 'education': 'EDUCAÇÃO', 'skills': 'COMPETÊNCIAS', 'personal_info': 'DADOS PESSOAIS', 'profile_summary': 'PERFIL PROFISSIONAL'}
}

# --- 5. FUNZIONI HELPER ---

def set_table_background(cell, color_hex):
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def add_bottom_border(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '20547D')
    pbdr.append(bottom)
    pPr.append(pbdr)

def process_image(image_file, border_width):
    img = Image.open(image_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return ImageOps.expand(img, border=border_width, fill='white')

def clean_text(text):
    if not text: return ""
    return text.replace("**", "").replace("##", "").strip()

# --- FUNZIONE CREAZIONE CV (CONGELATA) ---
def create_cv_docx(data, photo_stream, lang_code):
    doc = Document()
    section = doc.sections[0]
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.5)
    
    # Header Banner Blu
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    col0_width = Inches(1.2)
    col1_width = Inches(6.1)
    table.columns[0].width = col0_width
    table.columns[1].width = col1_width
    
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    row.height = Inches(2.0)
    
    cell_foto = row.cells[0]
    cell_text = row.cells[1]
    
    set_table_background(cell_foto, "20547D")
    set_table_background(cell_text, "20547D")
    
    # Foto
    cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if photo_stream:
        p_foto = cell_foto.paragraphs[0]
        p_foto.alignment = WD_ALIGN_PARAGRAPH.LEFT 
        p_foto.paragraph_format.space_before = Pt(0)
        p_foto.paragraph_format.space_after = Pt(0)
        p_foto.paragraph_format.left_indent = Pt(10) 
        run_foto = p_foto.add_run()
        run_foto.add_picture(photo_stream, height=Inches(1.5))
    
    # Testo Intestazione
    cell_text.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_name = cell_text.paragraphs[0]
    p_name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(0)
    p_name.paragraph_format.line_spacing = 1.0
    
    info = data.get('personal_info', {})
    full_name = f"{info.get('first_name', '')} {info.get('last_name', '')}"
    run_name = p_name.add_run(clean_text(full_name))
    run_name.font.size = Pt(26)
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    run_name.font.name = 'Arial'
    run_name.bold = True
    
    p_info = cell_text.add_paragraph()
    p_info.paragraph_format.space_before = Pt(6)
    p_info.paragraph_format.space_after = Pt(0)
    contact_str = f"{clean_text(info.get('address', ''))}\n{clean_text(info.get('phone', ''))} | {clean_text(info.get('email', ''))}"
    run_info = p_info.add_run(contact_str)
    run_info.font.size = Pt(10)
    run_info.font.color.rgb = RGBColor(220, 220, 220)
    run_info.font.name = 'Arial'
    
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    
    # Body
    titles = SECTION_TITLES.get(lang_code, SECTION_TITLES['en_us'])
    cv_sections = data.get('cv_sections', {})

    if cv_sections.get('profile_summary'):
        h = doc.add_heading(titles.get('profile_summary', 'PROFILE'), level=1)
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        h.runs[0].font.name = 'Arial'
        h.runs[0].font.size = Pt(12)
        h.runs[0].bold = True
        add_bottom_border(h)
        p = doc.add_paragraph(clean_text(cv_sections.get('profile_summary')))
        p.paragraph_format.space_after = Pt(12)

    sections_to_print = ['experience', 'education', 'skills', 'languages']
    for key in sections_to_print:
        content = cv_sections.get(key)
        if content:
            title_text = titles.get(key, key.upper())
            h = doc.add_heading(title_text, level=1)
            h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
            h.runs[0].font.name = 'Arial'
            h.runs[0].font.size = Pt(12)
            h.runs[0].bold = True
            add_bottom_border(h)
            
            if isinstance(content, list):
                for item in content:
                    doc.add_paragraph(clean_text(str(item)), style='List Bullet')
            else:
                doc.add_paragraph(clean_text(str(content)))
            doc.add_paragraph().paragraph_format.space_after = Pt(8)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- FUNZIONE CREAZIONE LETTERA (CONGELATA) ---
def create_letter_docx(letter_data, personal_info):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    sender_block = f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}\n"
    sender_block += f"{personal_info.get('address', '')}\n"
    sender_block += f"{personal_info.get('phone', '')}\n{personal_info.get('email', '')}"
    
    p_sender = doc.add_paragraph(clean_text(sender_block))
    p_sender.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_sender.runs[0].font.size = Pt(10)
    doc.add_paragraph() 
    
    date_str = letter_data.get('date_line', datetime.datetime.now().strftime("%d.%m.%Y"))
    p_date = doc.add_paragraph(clean_text(date_str))
    p_date.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_paragraph() 
    
    recipient = clean_text(letter_data.get('recipient_block', 'Hiring Manager'))
    p_rec = doc.add_paragraph(recipient)
    p_rec.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_paragraph() 
    
    subject = clean_text(letter_data.get('subject_line', 'Application'))
    p_sub = doc.add_paragraph()
    run_sub = p_sub.add_run(subject)
    run_sub.bold = True
    run_sub.font.size = Pt(14)
    doc.add_paragraph() 
    
    body = clean_text(letter_data.get('body_content', ''))
    doc.add_paragraph(body)
    doc.add_paragraph() 
    
    closing = clean_text(letter_data.get('closing', 'Freundliche Grüsse'))
    doc.add_paragraph(closing)
    
    for _ in range(4):
        doc.add_paragraph()
        
    doc.add_paragraph(f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 6. MAIN LOOP ---

def main():
    # Sidebar
    current_code = st.session_state.lang_code
    current_name = list(LANG_DISPLAY.keys())[0] 
    for name, code in LANG_DISPLAY.items():
        if code == current_code:
            current_name = name
            break
            
    current_label = TRANSLATIONS.get(current_code, TRANSLATIONS['it'])['lang_label']
    lang_name = st.sidebar.selectbox(current_label, list(LANG_DISPLAY.keys()), index=list(LANG_DISPLAY.keys()).index(current_name))
    
    new_lang_code = LANG_DISPLAY[lang_name]
    if new_lang_code != st.session_state.lang_code:
        st.session_state.lang_code = new_lang_code
        st.rerun()

    t = TRANSLATIONS[st.session_state.lang_code]
    st.title(t['main_title'])
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception:
        st.error("🚨 " + t.get('missing_key', 'API Key Error'))
        st.stop()
        
    st.sidebar.markdown("---")
    st.sidebar.subheader(t['sidebar_title'])
    uploaded_photo = st.sidebar.file_uploader(t['photo_label'], type=['jpg', 'png', 'jpeg'])
    border_width = st.sidebar.slider(t['border_label'], 0, 20, 5)
    
    if uploaded_photo:
        processed = process_image(uploaded_photo, border_width)
        st.session_state.processed_photo = processed
        st.sidebar.markdown(f"**{t['preview_label']}**")
        st.sidebar.image(processed, width=150)
        
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t['step1_title'])
        cv_file = st.file_uploader("CV", type=["pdf"], label_visibility="collapsed", help=t['upload_help'])
    with col2:
        st.subheader(t['step2_title'])
        job_desc = st.text_area("Job", height=150, placeholder=t['job_placeholder'], label_visibility="collapsed")
        
    st.markdown("---")
    
    if st.button(t['btn_label'], type="primary", use_container_width=True):
        if not cv_file or not job_desc:
            st.error(t['error'])
        else:
            with st.spinner(t['spinner_msg']):
                try:
                    # 1. Estrazione Testo
                    reader = pypdf.PdfReader(cv_file)
                    text = ""
                    for p in reader.pages: text += p.extract_text() + "\n"
                    
                    # 2. Chiama AI con GOOGLE SEARCH
                    # Configurazione strumento di ricerca
                    tools = [{"google_search": {}}]
                    model = genai.GenerativeModel("models/gemini-3-pro-preview", tools=tools)
                    
                    prompt = f"""
                    Role: Professional HR Expert.
                    Language: {lang_name}.
                    
                    Task: Analyze CV and Job Description.
                    
                    INSTRUCTIONS FOR LETTER:
                    1. **USE GOOGLE SEARCH** to find the official, complete physical address of the hiring company mentioned in the job offer. Do not guess. If search fails, use data from text.
                    2. If German language: Ensure body text starts with CAPITAL letter even after comma (e.g. "Sehr geehrte Damen und Herren,\n\nIch bewerbe mich...").
                    
                    OUTPUT JSON STRICTLY:
                    {{
                        "personal_info": {{ "first_name": "...", "last_name": "...", "email": "...", "phone": "...", "address": "..." }},
                        "cv_sections": {{
                            "profile_summary": "...",
                            "experience": ["...", "..."],
                            "education": ["..."],
                            "skills": ["..."],
                            "languages": ["..."]
                        }},
                        "letter_data": {{
                            "recipient_block": "Company Name\\nStreet\\nCity",
                            "date_line": "City, Date",
                            "subject_line": "Application for...",
                            "body_content": "Full text...",
                            "closing": "Freundliche Grüsse"
                        }}
                    }}
                    
                    CV: {text[:20000]}
                    JOB: {job_desc}
                    """
                    
                    response = model.generate_content(prompt)
                    
                    # Pulizia risposta per evitare errori JSON se il modello restituisce testo extra
                    json_str = response.text
                    # Cerca il primo { e l'ultimo }
                    start_idx = json_str.find('{')
                    end_idx = json_str.rfind('}') + 1
                    if start_idx != -1 and end_idx != -1:
                        json_str = json_str[start_idx:end_idx]
                    
                    data = json.loads(json_str)
                    
                    st.session_state.generated_data = data
                    st.success(t['success'])
                    
                except Exception as e:
                    st.error(f"{t['error']}: {str(e)}")
                    
    if st.session_state.generated_data:
        data = st.session_state.generated_data
        tab1, tab2 = st.tabs([t['tab_cv'], t['tab_letter']])
        
        with tab1:
            img_stream = None
            if st.session_state.processed_photo:
                img_stream = io.BytesIO()
                st.session_state.processed_photo.save(img_stream, format='JPEG')
                img_stream.seek(0)
                
            docx = create_cv_docx(data, img_stream, st.session_state.lang_code)
            
            st.download_button(
                label=f"📥 {t['down_cv']}",
                data=docx,
                file_name="CV_Optimized.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.json(data.get('cv_sections'))
            
        with tab2:
            letter_data = data.get('letter_data', {})
            docx_l = create_letter_docx(letter_data, data.get('personal_info', {}))
            
            st.download_button(
                label=f"📥 {t['down_let']}",
                data=docx_l,
                file_name="Cover_Letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.markdown(letter_data.get('body_content', ''))

if __name__ == "__main__":
    main()
