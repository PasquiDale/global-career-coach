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
import pypdf
from datetime import datetime
import json
import urllib.parse
try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Global Career Coach", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>div[data-baseweb="select"] > div { cursor: pointer !important; } button { cursor: pointer !important; }</style>""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'lang_code' not in st.session_state: st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state: st.session_state['generated_data'] = None
if 'processed_photo' not in st.session_state: st.session_state['processed_photo'] = None
if 'job_search_results' not in st.session_state: st.session_state['job_search_results'] = None
if 'pdf_ref' not in st.session_state: st.session_state['pdf_ref'] = None

# --- DIZIONARI ---
LANG_DISPLAY = {"Italiano": "it", "English (US)": "en_us", "English (UK)": "en_uk", "Deutsch (Deutschland)": "de_de", "Deutsch (Schweiz)": "de_ch", "Français": "fr", "Español": "es", "Português": "pt"}
TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carica CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'profile_title': 'PROFILO PERSONALE', 'search_sec_title': 'Cerca Lavoro', 'search_role': 'Che lavoro cerchi?', 'search_loc': 'Dove?', 'search_rad': 'Raggio (km)', 'search_btn': 'Trova Lavori 🔎', 'search_res_title': 'Offerte Trovate:', 'search_info': 'Copia il testo dell\'annuncio e incollalo sotto.', 'no_jobs': 'Nessun lavoro trovato.', 'upload_first': '⚠️ Carica prima il CV!'},
    'en_us': {'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE', 'search_sec_title': 'Job Search', 'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Copy the ad text and paste it below.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL', 'search_sec_title': 'Jobsuche', 'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Kopieren Sie den Text und fügen Sie ihn unten ein.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!'},
    'de_de': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL', 'search_sec_title': 'Jobsuche', 'search_role': 'Welcher Job?', 'search_loc': 'Wo?', 'search_rad': 'Umkreis (km)', 'search_btn': 'Jobs suchen 🔎', 'search_res_title': 'Gefundene Jobs:', 'search_info': 'Kopieren Sie den Text und fügen Sie ihn unten ein.', 'no_jobs': 'Keine Jobs gefunden.', 'upload_first': '⚠️ Zuerst Lebenslauf hochladen!'},
    'fr': {'sidebar_title': 'Paramètres du Profil', 'lang_label': 'Langue', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 'upload_help': 'Déposez le fichier ici', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte de l\'offre ici...', 'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 'success': 'Terminé!', 'error': 'Erreur', 'profile_title': 'PROFIL PROFESSIONNEL', 'search_sec_title': 'Recherche Emploi', 'search_role': 'Quel emploi ?', 'search_loc': 'Où ?', 'search_rad': 'Rayon (km)', 'search_btn': 'Trouver Emplois 🔎', 'search_res_title': 'Emplois trouvés :', 'search_info': 'Copiez le texte et collez-le ci-dessous.', 'no_jobs': 'Aucun emploi trouvé.', 'upload_first': '⚠️ Chargez d\'abord le CV!'},
    'es': {'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'profile_title': 'PERFIL PROFESIONAL', 'search_sec_title': 'Buscar Empleo', 'search_role': '¿Qué trabajo?', 'search_loc': '¿Dónde?', 'search_rad': 'Radio (km)', 'search_btn': 'Buscar Emplois 🔎', 'search_res_title': 'Empleos encontrados:', 'search_info': 'Copia el texto y pégalo abajo.', 'no_jobs': 'No se encontraron empleos.', 'upload_first': '⚠️ ¡Sube el CV primero!'},
    'pt': {'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'profile_title': 'PERFIL PROFISSIONAL', 'search_sec_title': 'Buscar Emprego', 'search_role': 'Qual trabalho?', 'search_loc': 'Onde?', 'search_rad': 'Raio (km)', 'search_btn': 'Buscar Empregos 🔎', 'search_res_title': 'Empregos encontrados:', 'search_info': 'Copie o texto e cole abaixo.', 'no_jobs': 'Nenhum emprego encontrado.', 'upload_first': '⚠️ Carregue o CV primeiro!'},
    'en_uk': {'sidebar_title': 'Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE', 'search_sec_title': 'Job Search', 'search_role': 'Job Title', 'search_loc': 'Location', 'search_rad': 'Radius (km)', 'search_btn': 'Find Jobs 🔎', 'search_res_title': 'Found Jobs:', 'search_info': 'Copy the ad text and paste it below.', 'no_jobs': 'No jobs found.', 'upload_first': '⚠️ Upload CV first!'}
}

SECTION_TITLES = {
    'it': {'experience': 'ESPERIENZA PROFESSIONALE', 'education': 'ISTRUZIONE', 'skills': 'COMPETENZE', 'languages': 'LINGUE', 'interests': 'INTERESSI', 'personal_info': 'DATI PERSONALI', 'profile_summary': 'PROFILO PERSONALE'},
    'de_ch': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHEN', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'de_de': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'languages': 'SPRACHEN', 'interests': 'INTERESSEN', 'personal_info': 'PERSÖNLICHE DATEN', 'profile_summary': 'PERSÖNLICHES PROFIL'},
    'fr': {'experience': 'EXPÉRIENCE PROFESSIONNELLE', 'education': 'FORMATION', 'skills': 'COMPÉTENCES', 'languages': 'LANGUES', 'interests': 'INTÉRÊTS', 'personal_info': 'INFORMATIONS PERSONNELLES', 'profile_summary': 'PROFIL PROFESSIONNEL'},
    'en_us': {'experience': 'PROFESSIONAL EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFILE'},
    'en_uk': {'experience': 'WORK EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'languages': 'LANGUAGES', 'interests': 'INTERESTS', 'personal_info': 'PERSONAL DETAILS', 'profile_summary': 'PROFILE'},
    'es': {'experience': 'EXPERIENCIA LABORAL', 'education': 'EDUCACIÓN', 'skills': 'HABILIDADES', 'languages': 'IDIOMAS', 'interests': 'INTERESES', 'personal_info': 'DATOS PERSONALES', 'profile_summary': 'PERFIL PROFESIONAL'},
    'pt': {'experience': 'EXPERIÊNCIA PROFISSIONAL', 'education': 'EDUCAÇÃO', 'skills': 'COMPETÊNCIAS', 'languages': 'IDIOMAS', 'interests': 'INTERESSES', 'personal_info': 'DADOS PESSOAIS', 'profile_summary': 'PERFIL PROFISSIONAL'}
}

# --- 5. FUNZIONI HELPER ---
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
    pdf_reader = pypdf.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# --- 6. CREATE CV DOCX ---
def create_cv_docx(json_data, pil_image, lang_code):
    doc = Document()
    
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(1.2)
    table.columns[1].width = Inches(6.1)
    
    row = table.rows[0]
    row.height = Inches(2.0)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    
    set_table_background(row.cells[0], "20547D")
    set_table_background(row.cells[1], "20547D")
    
    # Foto
    cell_foto = row.cells[0]
    cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if pil_image:
        img_s = io.BytesIO()
        pil_image.save(img_s, format='PNG')
        img_s.seek(0)
        p = cell_foto.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run()
        run.add_picture(img_s, height=Inches(1.5))
        
    # Testo
    cell_text = row.cells[1]
    cell_text.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_name = cell_text.paragraphs[0]
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(0)
    p_name.paragraph_format.line_spacing = 1.0
    run_name = p_name.add_run(json_data['personal_info'].get('name', ''))
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    run_name.font.size = Pt(24)
    run_name.bold = True
    
    p_info = cell_text.add_paragraph()
    p_info.paragraph_format.space_before = Pt(0)
    info = f"{json_data['personal_info'].get('address','')} | {json_data['personal_info'].get('phone','')} | {json_data['personal_info'].get('email','')}"
    run_info = p_info.add_run(info)
    run_info.font.color.rgb = RGBColor(255, 255, 255)
    
    doc.add_paragraph("")
    
    titles = SECTION_TITLES.get(lang_code, SECTION_TITLES['en_us'])
    
    if 'profile_summary' in json_data['cv_sections']:
        h = doc.add_paragraph(titles['profile_summary'])
        h.style = 'Heading 2'
        add_bottom_border(h)
        run_h = h.runs[0]
        run_h.font.color.rgb = RGBColor(32, 84, 125)
        run_h.font.bold = True
        doc.add_paragraph(json_data['cv_sections']['profile_summary'].replace('**', ''))
        doc.add_paragraph("")

    sections = ['experience', 'education', 'skills', 'languages', 'interests']
    for key in sections:
        if key in json_data['cv_sections'] and json_data['cv_sections'][key]:
            h = doc.add_paragraph(titles[key])
            h.style = 'Heading 2'
            add_bottom_border(h)
            run_h = h.runs[0]
            run_h.font.color.rgb = RGBColor(32, 84, 125)
            run_h.font.bold = True
            
            items = json_data['cv_sections'][key]
            if isinstance(items, list):
                for item in items:
                    p = doc.add_paragraph(item.replace('**', ''), style='List Bullet')
                    if key in ['experience', 'education']:
                        doc.add_paragraph("")
            else:
                doc.add_paragraph(str(items).replace('**', ''))
                doc.add_paragraph("")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 7. CREATE LETTER ---
def create_letter_docx(letter_data, personal_info, lang_code):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run(f"{personal_info.get('name')}\n{personal_info.get('address')}\n{personal_info.get('phone')}\n{personal_info.get('email')}")
    doc.add_paragraph("")
    p_date = doc.add_paragraph(get_todays_date(lang_code))
    p_date.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_paragraph("")
    doc.add_paragraph(letter_data.get('recipient_block', 'Recipient'))
    doc.add_paragraph("")
    p_subj = doc.add_paragraph(letter_data.get('subject_line', 'Subject'))
    p_subj.runs[0].bold = True
    p_subj.runs[0].font.size = Pt(14)
    doc.add_paragraph("")
    doc.add_paragraph(letter_data.get('body_content', 'Body'))
    doc.add_paragraph("")
    closing = letter_data.get('closing', 'Best regards').replace(personal_info.get('name', ''), '').strip()
    p_close = doc.add_paragraph(closing)
    p_close.paragraph_format.keep_with_next = True
    for _ in range(4): doc.add_paragraph("")
    doc.add_paragraph(personal_info.get('name', ''))
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 8. JOB SEARCH (SERPAPI) ---
def search_jobs_master(role, loc, rad, lang):
    if "SERPAPI_API_KEY" not in st.secrets:
        st.error("SERPAPI Key Missing")
        return []
    
    try:
        params = {
            "engine": "google_jobs",
            "q": f"{role} {loc}",
            "hl": lang,
            "radius": rad,
            "api_key": st.secrets["SERPAPI_API_KEY"]
        }
        search = GoogleSearch(params)
        results = search.get_dict().get("jobs_results", [])
        final_res = []
        
        for job in results[:10]:
            link = None
            if 'apply_options' in job and len(job['apply_options']) > 0:
                link = job['apply_options'][0].get('link')
            
            if not link and 'job_id' in job:
                link = f"https://www.google.com/search?ibp=htl;jobs#fpstate=tldetail&htivrt=jobs&htidocid={job['job_id']}"
            
            if not link:
                link = job.get('share_link')

            if link:
                final_res.append({
                    "company": job.get("company_name", "Company"),
                    "role_title": job.get("title", role),
                    "link": link
                })
        return final_res
    except Exception as e:
        st.error(f"Search Error: {e}")
        return []

# --- 9. AI GENERATION (GEMINI 2.5 PRO) ---
def get_gemini_response(pdf_text, job_text, lang_code):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel("models/gemini-2.5-pro")
        prompt = f"HR Expert. Create CV/Letter in {lang_code}. JSON Keys: personal_info, cv_sections (profile_summary, experience, education, skills, languages, interests), letter_data. NO AI MENTION."
        response = model.generate_content([prompt, pdf_text, job_text])
        return response.text
    except Exception as e:
        return str(e)

# --- 10. MAIN APP LOOP ---
with st.sidebar:
    lang_names = list(LANG_DISPLAY.keys())
    curr_code = st.session_state['lang_code']
    try:
        idx = list(LANG_DISPLAY.values()).index(curr_code)
    except:
        idx = 0
    
    t_temp = TRANSLATIONS.get(curr_code, TRANSLATIONS['it'])
    lang_label = t_temp.get('lang_label', 'Lingua')
    
    selected_name = st.selectbox(lang_label, lang_names, index=idx)
    st.session_state['lang_code'] = LANG_DISPLAY[selected_name]
    t = TRANSLATIONS[st.session_state['lang_code']]
    
    st.title(t['sidebar_title'])
    
    up_photo = st.file_uploader(t['photo_label'], type=['jpg','png'])
    border = st.slider(t['border_label'], 0, 50, 5)
    st.session_state['processed_photo'] = process_image(up_photo, border)
    if st.session_state['processed_photo']:
        st.image(st.session_state['processed_photo'], caption=t['preview_label'])
        
    st.divider()
    st.subheader(t.get('search_sec_title', 'Job Search'))
    role = st.text_input(t['search_role'])
    loc = st.text_input(t['search_loc'])
    rad = st.slider(t['search_rad'], 0, 100, 20)
    
    if st.button(t['search_btn']):
        if st.session_state.get('pdf_ref'):
            st.session_state['job_search_results'] = search_jobs_master(role, loc, rad, st.session_state['lang_code'])
        else:
            st.error(t['upload_first'])

# Main
t = TRANSLATIONS[st.session_state['lang_code']]
st.title(t['main_title'])

if st.session_state['job_search_results']:
    st.success(t['search_res_title'])
    st.info(t['search_info'])
    for job in st.session_state['job_search_results']:
        st.markdown(f"**{job['role_title']}** @ {job['company']}")
        st.markdown(f"[👉 Link]({job['link']})")
        st.divider()

st.subheader(t['step1_title'])
pdf_file = st.file_uploader(t['step1_title'], type=['pdf'], label_visibility='collapsed', key='main_pdf', help=t['upload_help'])
if pdf_file: st.session_state['pdf_ref'] = pdf_file

st.subheader(t['step2_title'])
job_desc = st.text_area("job", placeholder=t['job_placeholder'], height=200, label_visibility="collapsed")

if st.button(t['btn_label']):
    if pdf_file and job_desc:
        with st.spinner(t['spinner_msg']):
            pdf_txt = extract_text_from_pdf(pdf_file)
            json_res = get_gemini_response(pdf_txt, job_desc, st.session_state['lang_code'])
            json_res = json_res.replace("```json", "").replace("```", "")
            try:
                data = json.loads(json_res)
                st.session_state['generated_data'] = data
                st.success(t['success'])
            except:
                st.error(t['error'])
    else:
        st.warning(t['upload_first'])

if st.session_state['generated_data']:
    d = st.session_state['generated_data']
    t1, t2 = st.tabs([t['tab_cv'], t['tab_letter']])
    with t1:
        doc = create_cv_docx(d, st.session_state['processed_photo'], st.session_state['lang_code'])
        st.download_button(t['down_cv'], doc.getvalue(), "CV.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with t2:
        doc = create_letter_docx(d['letter_data'], d['personal_info'], st.session_state['lang_code'])
        st.download_button(t['down_let'], doc.getvalue(), "Letter.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
