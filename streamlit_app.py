import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
import io
from PIL import Image, ImageOps
import PyPDF2
from datetime import datetime
import json
import urllib.parse

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Global Career Coach", layout="wide", initial_sidebar_state="expanded")

# 2. CSS INJECTION
st.markdown("""
    <style>
    div[data-baseweb="select"] > div { cursor: pointer !important; }
    button { cursor: pointer !important; }
    </style>
""", unsafe_allow_html=True)

# 3. INIZIALIZZAZIONE SESSION STATE (RESET COMPLETO)
if 'lang_code' not in st.session_state:
    st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None
if 'processed_photo' not in st.session_state:
    st.session_state['processed_photo'] = None
if 'job_search_results' not in st.session_state:
    st.session_state['job_search_results'] = None

# 4. COSTANTI
LANG_DISPLAY = {
    "Italiano": "it", "English (US)": "en_us", "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de", "Deutsch (Schweiz)": "de_ch",
    "Français": "fr", "Español": "es", "Português": "pt"
}

# DIZIONARIO TRADUZIONI CORRETTO E COMPLETO
TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carica CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'profile_title': 'PROFILO PERSONALE', 'search_role': 'Che lavoro cerchi?', 'search_loc': 'Dove?', 'search_rad': 'Raggio (km)', 'search_btn': 'Trova Lavori 🔎', 'search_res_title': 'Offerte Trovate:', 'search_info': 'Copia il testo dell\'annuncio e incollalo sotto.', 'no_jobs': 'Nessun lavoro trovato.', 'upload_first': '⚠️ Carica prima il CV!'},
    'en_us': {'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE', 'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Copy the ad text and paste it below.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL', 'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Kopieren Sie den Text und fügen Sie ihn unten ein.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!'},
    'de_de': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL', 'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Kopieren Sie den Text und fügen Sie ihn unten ein.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!'},
    'fr': {'sidebar_title': 'Paramètres du Profil', 'lang_label': 'Langue', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 'upload_help': 'Déposez le fichier ici', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte de l\'offre ici...', 'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 'success': 'Terminé!', 'error': 'Erreur', 'profile_title': 'PROFIL PROFESSIONNEL', 'search_role': 'Quel emploi ?', 'search_loc': 'Où ?', 'search_rad': 'Rayon (km)', 'search_btn': 'Trouver Emplois 🔎', 'search_res_title': 'Emplois trouvés :', 'search_info': 'Copiez le texte et collez-le ci-dessous.', 'no_jobs': 'Aucun emploi trouvé.', 'upload_first': '⚠️ Chargez d\'abord le CV!'},
    'es': {'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'profile_title': 'PERFIL PROFESIONAL', 'search_role': '¿Qué trabajo?', 'search_loc': '¿Dónde?', 'search_rad': 'Radio (km)', 'search_btn': 'Buscar Empleos 🔎', 'search_res_title': 'Empleos encontrados:', 'search_info': 'Copia el texto y pégalo abajo.', 'no_jobs': 'No se encontraron empleos.', 'upload_first': '⚠️ ¡Sube el CV primero!'},
    'pt': {'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'profile_title': 'PERFIL PROFISSIONAL', 'search_role': 'Qual trabalho?', 'search_loc': 'Onde?', 'search_rad': 'Raio (km)', 'search_btn': 'Buscar Empregos 🔎', 'search_res_title': 'Empregos encontrados:', 'search_info': 'Copie o texto e cole abaixo.', 'no_jobs': 'Nenhum emprego encontrado.', 'upload_first': '⚠️ Carregue o CV primeiro!'},
    'en_uk': {'sidebar_title': 'Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE', 'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Copy the ad text and paste it below.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!'}
}

SECTION_TITLES = {
    'it': {'experience': 'ESPERIENZA PROFESSIONALE', 'education': 'ISTRUZIONE', 'skills': 'COMPETENZE', 'languages': 'LINGUE', 'interests': 'INTERESSI', 'personal_info': 'DATI PERSONALI', 'profile_summary': 'PROFILO PERSONALE'},
    'de_ch': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHEN', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'de_de': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHEN', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'fr': {'experience': 'EXPÉRIENCE PROFESSIONNELLE', 'education': 'FORMATION', 'skills': 'COMPÉTENCES', 'languages': 'LANGUES', 'interests': 'INTÉRÊTS', 'personal_info': 'INFORMATIONS PERSONNELLES', 'profile_summary': 'PROFIL PROFESSIONNEL'},
    'en_us': {'experience': 'PROFESSIONAL EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFESSIONAL PROFILE'},
    'en_uk': {'experience': 'WORK EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFESSIONAL PROFILE'},
    'es': {'experience': 'EXPERIENCIA LABORAL', 'education': 'EDUCACIÓN', 'skills': 'HABILIDADES', 'languages': 'IDIOMAS', 'interests': 'INTERESES', 'personal_info': 'DATOS PERSONALES', 'profile_summary': 'PERFIL PROFESIONAL'},
    'pt': {'experience': 'EXPERIÊNCIA PROFISSIONAL', 'education': 'EDUCAÇÃO', 'skills': 'COMPETÊNCIAS', 'languages': 'IDIOMAS', 'interests': 'INTERESSES', 'personal_info': 'DADOS PESSOAIS', 'profile_summary': 'PERFIL PROFISSIONAL'}
}

# 5. FUNZIONI HELPER
def set_table_background(cell, color_hex):
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def add_bottom_border(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = parse_xml(r'<w:pBdr {}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="20547D"/></w:pBdr>'.format(nsdecls('w')))
    pPr.append(pBdr)

def process_image(image_file, border_width):
    if image_file is None: return None
    image = Image.open(image_file)
    if border_width > 0:
        image = ImageOps.expand(image, border=border_width, fill='white')
    return image

def get_todays_date(lang_code):
    now = datetime.now()
    if lang_code in ['de_ch', 'de_de', 'it', 'fr', 'es', 'pt']:
        return now.strftime("%d.%m.%Y")
    return now.strftime("%B %d, %Y")

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# 6. CREATE CV DOCX
def create_cv_docx(json_data, pil_image, lang_code):
    doc = Document()
    
    # Header Table
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(1.2)
    table.columns[1].width = Inches(6.1)
    
    row = table.rows[0]
    row.height = Inches(2.0)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    
    set_table_background(row.cells[0], "20547D")
    set_table_background(row.cells[1], "20547D")
    
    # Foto (Left)
    cell_foto = row.cells[0]
    cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if pil_image:
        img_stream = io.BytesIO()
        pil_image.save(img_stream, format='PNG')
        img_stream.seek(0)
        p = cell_foto.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.s
