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
        transition: transform 0.2s;
    }
    .job-card:hover { transform: translateY(-2px); }
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
           'search_role': 'Che lavoro cerchi?', 'search_loc': 'Dove?', 'search_rad': 'Raggio (km)', 'search_btn': 'Trova Lavori 🔎', 'search_res_title': 'Offerte Trovate:', 'search_info': 'Ecco alcune opportunità rilevate.', 'no_jobs': 'Nessun lavoro trovato.', 'upload_first': '⚠️ Carica prima il CV!', 'search_head': 'Ricerca Lavoro', 'search_hint': 'Carica Foto e CV per attivare la ricerca'},
    'en_us': {'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE',
              'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Here are some found opportunities.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!', 'search_head': 'Job Search', 'search_hint': 'Upload Photo and CV to enable search'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL',
              'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Hier sind einige gefundene Angebote.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!', 'search_head': 'Jobsuche', 'search_hint': 'Laden Sie Foto und CV hoch, um die Suche zu aktivieren'},
    'de_de': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL',
              'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Hier sind einige gefundene Angebote.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!', 'search_head': 'Jobsuche', 'search_hint': 'Laden Sie Foto und CV hoch, um die Suche zu aktivieren'},
    'fr': {'sidebar_title': 'Paramètres du Profil', 'lang_label': 'Langue', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 'upload_help': 'Déposez le fichier ici', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte de l\'offre ici...', 'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 'success': 'Terminé!', 'error': 'Erreur', 'profile_title': 'PROFIL PROFESSIONNEL',
           'search_role': 'Quel emploi ?', 'search_loc': 'Où ?', 'search_rad': 'Rayon (km)', 'search_btn': 'Trouver Emplois 🔎', 'search_res_title': 'Emplois trouvés :', 'search_info': 'Voici quelques opportunités trouvées.', 'no_jobs': 'Aucun emploi trouvé.', 'upload_first': '⚠️ Chargez d\'abord le CV!', 'search_head': 'Recherche d\'emploi', 'search_hint': 'Chargez Photo et CV pour activer la recherche'},
    'es': {'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'profile_title': 'PERFIL PROFESIONAL',
           'search_role': '¿Qué trabajo?', 'search_loc': '¿Dónde?', 'search_rad': 'Radio (km)', 'search_btn': 'Buscar Empleos 🔎', 'search_res_title': 'Empleos encontrados:', 'search_info': 'Aquí hay algunas oportunidades encontradas.', 'no_jobs': 'No se encontraron empleos.', 'upload_first': '⚠️ ¡Sube el CV primero!', 'search_head': 'Búsqueda de empleo', 'search_hint': 'Sube Foto y CV para activar la búsqueda'},
    'pt': {'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'profile_title': 'PERFIL PROFISSIONAL',
           'search_role': 'Qual trabalho?', 'search_loc': 'Onde?', 'search_rad': 'Raio (km)', 'search_btn': 'Buscar Empregos 🔎', 'search_res_title': 'Empregos encontrados:', 'search_info': 'Aqui estão algumas oportunidades encontradas.', 'no_jobs': 'Nenhum emprego encontrado.', 'upload_first': '⚠️ Carregue o CV primeiro!', 'search_head': 'Busca de emprego', 'search_hint': 'Carregue Foto e CV para ativar a busca'},
    'en_uk': {'sidebar_title': 'Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE',
              'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Here are some found opportunities.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!', 'search_head': 'Job Search', 'search_hint': 'Upload Photo and CV to enable search'}
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
    sectio
