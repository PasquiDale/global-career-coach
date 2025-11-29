import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from PIL import Image, ImageOps
import io
import datetime
import json
import pypdf
import urllib.parse

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Global Career Coach", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS INJECTION ---
st.markdown("""
    <style>
    div[data-baseweb="select"] > div { cursor: pointer !important; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    .job-card { 
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
        border-left: 5px solid #20547D; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .job-card h4 { margin-top: 0; color: #20547D; margin-bottom: 5px; }
    .job-link { 
        text-decoration: none; 
        color: white !important; 
        background-color: #20547D; 
        padding: 8px 16px; 
        border-radius: 5px; 
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
    }
    .job-link:hover { background-color: #163b57; }
    </style>
""", unsafe_allow_html=True)

# --- 3. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state: st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state: st.session_state['generated_data'] = None
if 'processed_photo' not in st.session_state: st.session_state['processed_photo'] = None
if 'job_search_results' not in st.session_state: st.session_state['job_search_results'] = None
if 'cv_text_content' not in st.session_state: st.session_state['cv_text_content'] = ""

# --- 4. COSTANTI E DIZIONARI ---

LANG_DISPLAY = {
    "Italiano": "it", "English (US)": "en_us", "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de", "Deutsch (Schweiz)": "de_ch",
    "Français": "fr", "Español": "es", "Português": "pt"
}

TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carica CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'profile_title': 'PROFILO PERSONALE',
           'search_role': 'Che lavoro cerchi?', 'search_loc': 'Dove?', 'search_rad': 'Raggio (km)', 'search_btn': 'Trova Lavori 🔎', 'search_res_title': 'Offerte Trovate:', 'search_info': 'Ecco alcune opportunità. Clicca sul pulsante per cercare su Google Jobs.', 'no_jobs': 'Nessun lavoro trovato.', 'upload_first': '⚠️ Carica prima il CV!', 'search_head': 'Ricerca Lavoro', 'search_hint': 'Carica Foto e CV per attivare la ricerca'},
    'en_us': {'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE',
              'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Here are some opportunities. Click the button to search on Google Jobs.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!', 'search_head': 'Job Search', 'search_hint': 'Upload Photo and CV to enable search'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL',
              'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Hier sind einige Angebote. Klicken Sie auf den Button, um auf Google Jobs zu suchen.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!', 'search_head': 'Jobsuche', 'search_hint': 'Laden Sie Foto und CV hoch, um die Suche zu aktivieren'},
    'de_de': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL',
              'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Hier sind einige Angebote. Klicken Sie auf den Button, um auf Google Jobs zu suchen.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!', 'search_head': 'Jobsuche', 'search_hint': 'Laden Sie Foto und CV hoch, um die Suche zu aktivieren'},
    'fr': {'sidebar_title': 'Paramètres du Profil', 'lang_label': 'Langue', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 'upload_help': 'Déposez le fichier ici', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte de l\'offre ici...', 'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 'success': 'Terminé!', 'error': 'Erreur', 'profile_title': 'PROFIL PROFESSIONNEL',
           'search_role': 'Quel emploi ?', 'search_loc': 'Où ?', 'search_rad': 'Rayon (km)', 'search_btn': 'Trouver Emplois 🔎', 'search_res_title': 'Emplois trouvés :', 'search_info': 'Voici quelques opportunités. Cliquez sur le bouton pour chercher sur Google Jobs.', 'no_jobs': 'Aucun emploi trouvé.', 'upload_first': '⚠️ Chargez d\'abord le CV!', 'search_head': 'Recherche d\'emploi', 'search_hint': 'Chargez Photo et CV pour activer la recherche'},
    'es': {'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'profile_title': 'PERFIL PROFESIONAL',
           'search_role': '¿Qué trabajo?', 'search_loc': '¿Dónde?', 'search_rad': 'Radio (km)', 'search_btn': 'Buscar Empleos 🔎', 'search_res_title': 'Empleos encontrados:', 'search_info': 'Aquí hay oportunidades. Haz clic en el botón para buscar en Google Jobs.', 'no_jobs': 'No se encontraron empleos.', 'upload_first': '⚠️ ¡Sube el CV primero!', 'search_head': 'Búsqueda de empleo', 'search_hint': 'Sube Foto y CV para activar la búsqueda'},
    'pt': {'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'profile_title': 'PERFIL PROFISSIONAL',
           'search_role': 'Qual trabalho?', 'search_loc': 'Onde?', 'search_rad': 'Raio (km)', 'search_btn': 'Buscar Empregos 🔎', 'search_res_title': 'Empregos encontrados:', 'search_info': 'Aqui estão algumas oportunidades. Clique no botão para buscar no Google Jobs.', 'no_jobs': 'Nenhum emprego encontrado.', 'upload_first': '⚠️ Carregue o CV primeiro!', 'search_head': 'Busca de emprego', 'search_hint': 'Carregue Foto e CV para ativar a busca'},
    'en_uk': {'sidebar_title': 'Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE',
              'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Here are some opportunities. Click the button to search on Google Jobs.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!', 'search_head': 'Job Search', 'search_hint': 'Upload Photo and CV to enable search'}
}

SECTION_TITLES = {
    'it': ["PROFILO PERSONALE", "ESPERIENZA PROFESSIONALE", "ISTRUZIONE E FORMAZIONE", "COMPETENZE LINGUISTICHE", "COMPETENZE TECNICHE"],
    'en_us': ["PROFESSIONAL PROFILE", "PROFESSIONAL EXPERIENCE", "EDUCATION", "LANGUAGES", "SKILLS"],
    'en_uk': ["PROFESSIONAL PROFILE", "WORK EXPERIENCE", "EDUCATION", "LANGUAGES", "SKILLS"],
    'de_ch': ["PERSÖNLICHES PROFIL", "BERUFSERFAHRUNG", "AUSBILDUNG", "SPRACHKENNTNISSE", "FÄHIGKEITEN"],
    'de_de': ["PERSÖNLICHES PROFIL", "BERUFSERFAHRUNG", "AUSBILDUNG", "SPRACHKENNTNISSE", "FÄHIGKEITEN"],
    'fr': ["PROFIL PROFESSIONNEL", "EXPÉRIENCE PROFESSIONNELLE", "FORMATION", "LANGUES", "COMPÉTENCES"],
    'es': ["PERFIL PROFESIONAL", "EXPERIENCIA PROFESIONAL", "EDUCACIÓN", "IDIOMAS", "HABILIDADES"],
    'pt': ["PERFIL PROFISSIONAL", "EXPERIÊNCIA PROFISSIONAL", "EDUCAÇÃO", "IDIOMAS", "COMPETÊNCIAS"]
}

# --- 5. FUNZIONI HELPER ---

def set_table_background(table, color_hex):
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        tbl_pr = parse_xml(r'<w:tblPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:tblPr>')
        table._tbl.insert(0, tbl_pr)
    shd = parse_xml(f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="{color_hex}"/>')
    tbl_pr.append(shd)

def add_bottom_border(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(nsdecls('w'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pbdr.append(bottom)
    pPr.append(pbdr)

def process_image(uploaded_file, border_size=0):
    if uploaded_file is None: return None
    try:
        img = Image.open(uploaded_file)
        if border_size > 0:
            img = ImageOps.expand(img, border=border_size, fill='white')
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=img.format if img.format else 'JPEG')
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception:
        return None

def get_todays_date(lang_code):
    today = datetime.date.today()
    if 'de' in lang_code: return today.strftime("%d.%m.%Y")
    elif 'en_us' in lang_code: return today.strftime("%B %d, %Y")
    else: return today.strftime("%d/%m/%Y")

def extract_text_from_pdf(pdf_file):
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except: return ""

# --- 6. FUNZIONE GENERAZIONE DOCX (CV) ---
def create_cv_docx(data, photo_stream, lang_code):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    # Header Blu
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.allow_autofit = False
    set_table_background(table, "20547D")
    
    col0 = table.columns[0]
    col0.width = Inches(1.5)
    cell_foto = table.cell(0, 0)
    cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    if photo_stream:
        try:
            paragraph = cell_foto.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            run.add_picture(photo_stream, width=Inches(1.2))
        except: pass

    col1 = table.columns[1]
    col1.width = Inches(6.0)
    cell_text = table.cell(0, 1)
    cell_text.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    p_name = cell_text.paragraphs[0]
    p_name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_name = p_name.add_run(f"{data.get('nome', '')} {data.get('cognome', '')}")
    run_name.font.name = 'Arial'
    run_name.font.size = Pt(24)
    run_name.font.bold = True
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    
    p_contact = cell_text.add_paragraph()
    p_contact.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_contact.space_before = Pt(2)
    contacts = []
    if data.get('indirizzo'): contacts.append(data.get('indirizzo'))
    if data.get('telefono'): contacts.append(data.get('telefono'))
    if data.get('email'): contacts.append(data.get('email'))
    if data.get('linkedin'): contacts.append(data.get('linkedin'))
    contact_str = " • ".join(contacts)
    run_contact = p_contact.add_run(contact_str)
    run_contact.font.name = 'Arial'
    run_contact.font.size = Pt(10)
    run_contact.font.color.rgb = RGBColor(255, 255, 255)

    doc.add_paragraph()

    def add_section_title(title):
        p = doc.add_paragraph()
        p.space_before = Pt(12)
        p.space_after = Pt(3)
        add_bottom_border(p)
        run = p.add_run(title.upper())
        run.font.name = 'Arial'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(32, 84, 125)

    def add_body_text(text, bold=False):
        if not text: return
        p = doc.add_paragraph()
        p.space_after = Pt(2)
        run = p.add_run(text)
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.font.bold = bold

    if data.get('profilo'):
        add_section_title(TRANSLATIONS[lang_code]['profile_title'])
        add_body_text(data.get('profilo'))

    if data.get('esperienze'):
        add_section_title(SECTION_TITLES[lang_code][1])
        for exp in data['esperienze']:
            role_line = f"{exp.get('ruolo', '')}"
            if exp.get('azienda'): role_line += f" | {exp.get('azienda')}"
            date_line = f"{exp.get('data_inizio', '')} - {exp.get('data_fine', '')}"
            if exp.get('luogo'): date_line += f" | {exp.get('luogo')}"
            
            p_head = doc.add_paragraph()
            p_head.space_before = Pt(8)
            p_head.space_after = Pt(0)
            run_h = p_head.add_run(role_line)
            run_h.font.name = 'Arial'
            run_h.font.size = Pt(11)
            run_h.font.bold = True
            
            p_sub = doc.add_paragraph()
            p_sub.space_after = Pt(2)
            run_s = p_sub.add_run(date_line)
            run_s.font.name = 'Arial'
            run_s.font.size = Pt(9)
            run_s.font.italic = True
            run_s.font.color.rgb = RGBColor(100, 100, 100)

            if exp.get('descrizione'):
                add_body_text(exp.get('descrizione'))
                doc.add_paragraph("") 

    if data.get('istruzione'):
        add_section_title(SECTION_TITLES[lang_code][2])
        for edu in data['istruzione']:
            title = f"{edu.get('titolo', '')}"
            if edu.get('istituto'): title += f", {edu.get('istituto')}"
            add_body_text(title, bold=True)
            add_body_text(f"{edu.get('anno', '')}")

    if data.get('lingue'):
        add_section_title(SECTION_TITLES[lang_code][3])
        add_body_text(data.get('lingue'))

    if data.get('skills'):
        add_section_title(SECTION_TITLES[lang_code][4])
        add_body_text(data.get('skills'))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 7. FUNZIONE GENERAZIONE DOCX (LETTERA) ---
def create_letter_docx(data, lang_code):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)

    doc.add_paragraph(f"{data.get('nome', '')} {data.get('cognome', '')}")
    doc.add_paragraph(data.get('indirizzo', ''))
    doc.add_paragraph(data.get('email', ''))
    doc.add_paragraph(data.get('telefono', ''))
    doc.add_paragraph()
    doc.add_paragraph(get_todays_date(lang_code))
    doc.add_paragraph()

    body = data.get('lettera_testo', '')
    body = body.replace('**', '').replace('##', '')
    
    for paragraph in body.split('\n'):
        if paragraph.strip():
            p = doc.add_paragraph(paragraph.strip())
            p.paragraph_format.space_after = Pt(6)

    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph(f"{data.get('nome', '')} {data.get('cognome', '')}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 8. FUNZIONE JOB SEARCH (SMART - NO AI TOOLS) ---
def search_jobs_smart(role, location, radius, lang):
    """
    Usa Gemini per trovare Nomi Aziende/Ruoli, poi PYTHON crea i link Google.
    ZERO TOOLS = ZERO ERRORI.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        
        # Modello standard 1.5 Pro (Molto intelligente per trovare aziende)
        model = genai.GenerativeModel("models/gemini-1.5-pro")
        
        prompt = f"""
        Act as a Career Coach/Recruiter in {lang}.
        Goal: Identify 5 companies or organizations in '{location}' (within {radius} km) that are known to hire for '{role}' roles.
        
        INSTRUCTIONS:
        1. Identify real companies/hospitals/institutions in that area.
        2. Identify the specific job title used in that language/region for '{role}'.
        3. Return ONLY a valid JSON list.
        4. JSON Format: [{{"company": "Name", "role_title": "Specific Role Title", "portal": "LinkedIn/Indeed/Direct"}}]
        5. DO NOT invent URLs. I will generate them programmatically.
        """
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Pulizia JSON
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text: text = text.split("```")[1].split("```")[0]
        
        data = json.loads(text)
        
        # PYTHON LINK GENERATOR (Infallibile)
        for item in data:
            # Query di ricerca ottimizzata per Google Jobs
            query = f"{item['role_title']} {item['company']} {location} jobs"
            safe_query = urllib.parse.quote(query)
            # Link magico che apre l'interfaccia "Google Jobs"
            item['link'] = f"https://www.google.com/search?q={safe_query}&ibp=htl;jobs"
            
        return data
        
    except Exception as e:
        st.error(f"Search Error: {e}")
        return []

# --- 9. FUNZIONE AI GENERATIVA (GEMINI 3 PRO PREVIEW) ---
def generate_docs_ai(pdf_text, job_desc, lang_code):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        prompt = f"""
        Act as a professional HR Resume Writer.
        Language for output: {lang_code} (STRICTLY).
        
        INPUT DATA:
        CV Text: {pdf_text}
        Job Description: {job_desc}
        
        TASK:
        1. Extract personal data (Name, Surname, Address, Phone, Email, LinkedIn).
        2. Rewrite the CV content to match the Job Description. Use Action Verbs.
        3. Write a tailored Cover Letter.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "nome": "...", "cognome": "...", "indirizzo": "...", "telefono": "...", "email": "...", "linkedin": "...",
            "profilo": "Short professional summary...",
            "esperienze": [
                {{"ruolo": "...", "azienda": "...", "data_inizio": "...", "data_fine": "...", "luogo": "...", "descrizione": "Bullet points..."}}
            ],
            "istruzione": [
                {{"titolo": "...", "istituto": "...", "anno": "..."}}
            ],
            "lingue": "...",
            "skills": "...",
            "lettera_testo": "Full body of the cover letter..."
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text: text = text.split("```")[1].split("```")[0]
            
        return json.loads(text)

    except Exception as e:
        st.error(f"Generation Error: {e}")
        return None

# --- 10. INTERFACCIA UTENTE (SIDEBAR) ---
with st.sidebar:
    st.title(TRANSLATIONS[st.session_state['lang_code']]['sidebar_title'])
    
    lang_selection = st.selectbox(
        TRANSLATIONS[st.session_state['lang_code']]['lang_label'],
        list(LANG_DISPLAY.keys()),
        index=list(LANG_DISPLAY.values()).index(st.session_state['lang_code'])
    )
    st.session_state['lang_code'] = LANG_DISPLAY[lang_selection]
    t = TRANSLATIONS[st.session_state['lang_code']]
    
    st.divider()
    
    st.subheader(t['photo_label'])
    uploaded_photo = st.file_uploader("Upload", type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")
    border_size = st.slider(t['border_label'], 0, 10, 2)
    
    if uploaded_photo:
        st.session_state['processed_photo'] = process_image(uploaded_photo, border_size)
        st.image(st.session_state['processed_photo'], caption=t['preview_label'], width=150)
    
    st.divider()
    
    # --- JOB SEARCH SECTION ---
    st.subheader(t['search_head'])
    st.caption(t['search_hint'])
    search_role = st.text_input(t['search_role'])
    search_loc = st.text_input(t['search_loc'])
    search_rad = st.slider(t['search_rad'], 10, 100, 25)
    
    if st.button(t['search_btn']):
        # CONTROLLO CV CARICATO
        if st.session_state.get('cv_text_content'):
            with st.spinner("Searching..."):
                results = search_jobs_smart(search_role, search_loc, search_rad, st.session_state['lang_code'])
                st.session_state['job_search_results'] = results
        else:
            st.error(t['upload_first'])

# --- 11. INTERFACCIA UTENTE (MAIN) ---
t = TRANSLATIONS[st.session_state['lang_code']]
st.title(t['main_title'])

# --- DISPLAY JOB RESULTS ---
if st.session_state['job_search_results']:
    st.info(t['search_info'])
    st.subheader(t['search_res_title'])
    if len(st.session_state['job_search_results']) > 0:
        for job in st.session_state['job_search_results']:
            # Card Risultato
            st.markdown(f"""
            <div class="job-card">
                <h4>{job.get('role_title', 'Job')} @ {job.get('company', 'Company')}</h4>
                <p>Fonte probabile: {job.get('portal', 'Web')}</p>
                <a href="{job.get('link', '#')}" target="_blank" class="job-link">
                    {t['search_btn']} (Google Jobs) 
                </a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning(t['no_jobs'])
    st.divider()

# --- INPUT SECTION ---
col1, col2 = st.columns(2)

with col1:
    st.subheader(t['step1_title'])
    uploaded_cv = st.file_uploader("PDF", type=['pdf'], label_visibility="collapsed", help=t['upload_help'])
    if uploaded_cv:
        text_content = extract_text_from_pdf(uploaded_cv)
        if text_content:
            st.session_state['cv_text_content'] = text_content

with col2:
    st.subheader(t['step2_title'])
    job_desc = st.text_area("Job", height=200, placeholder=t['job_placeholder'], label_visibility="collapsed")

if st.button(t['btn_label'], type="primary"):
    if uploaded_cv and job_desc:
        with st.spinner(t['spinner_msg']):
            data = generate_docs_ai(st.session_state['cv_text_content'], job_desc, st.session_state['lang_code'])
            
            if data:
                st.session_state['generated_data'] = data
                st.success(t['success'])
            else:
                st.error(t['error'])
    else:
        st.warning("Please upload CV and paste Job Description.")

# --- OUTPUT SECTION ---
if st.session_state['generated_data']:
    st.divider()
    data = st.session_state['generated_data']
    
    tab1, tab2 = st.tabs([t['tab_cv'], t['tab_letter']])
    
    with tab1: # CV
        cv_docx = create_cv_docx(data, st.session_state['processed_photo'], st.session_state['lang_code'])
        st.download_button(
            label=f"📥 {t['down_cv']}",
            data=cv_docx,
            file_name=f"CV_{data.get('cognome', 'Candidate')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.markdown(f"### {data.get('nome')} {data.get('cognome')}")
        st.markdown(f"**{data.get('profilo')}**")
        
    with tab2: # LETTERA
        let_docx = create_letter_docx(data, st.session_state['lang_code'])
        st.download_button(
            label=f"📥 {t['down_let']}",
            data=let_docx,
            file_name="Cover_Letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.text_area("Preview", value=data.get('lettera_testo', ''), height=400)
