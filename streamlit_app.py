import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import json
import pypdf
from PIL import Image, ImageOps

# --- 1. CONFIGURAZIONE PAGINA (TASSATIVAMENTE PRIMA RIGA) ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None
if 'processed_photo_bytes' not in st.session_state:
    st.session_state['processed_photo_bytes'] = None

# --- 3. DIZIONARIO TRADUZIONI COMPLETO ---
TRANSLATIONS = {
    'it': {
        'name': 'Italiano', 'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima Foto', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Carica il tuo CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta di lavoro...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Analisi e scrittura in corso con Gemini 3 Pro...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'missing_key': 'Chiave API mancante nei Secrets.', 'missing_inputs': 'Per favore carica sia il PDF che il testo dell\'annuncio.'
    },
    'en_us': {
        'name': 'English (US)', 'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Photo Preview', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer text here...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Analyzing with Gemini 3 Pro...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'missing_key': 'API Key missing in Secrets.', 'missing_inputs': 'Please upload PDF and paste Job Description.'
    },
    'en_uk': {
        'name': 'English (UK)', 'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Photo Preview', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer text here...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Analysing with Gemini 3 Pro...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'missing_key': 'API Key missing in Secrets.', 'missing_inputs': 'Please upload PDF and paste Job Description.'
    },
    'de_ch': {
        'name': 'Deutsch (CH)', 'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenbeschrieb', 'job_placeholder': 'Stellenanzeige hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Analyse läuft mit Gemini 3 Pro...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt.', 'missing_inputs': 'Bitte PDF hochladen und Stellenanzeige einfügen.'
    },
    'de_de': {
        'name': 'Deutsch (DE)', 'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige hier einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Analyse läuft mit Gemini 3 Pro...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt.', 'missing_inputs': 'Bitte PDF hochladen und Stellenanzeige einfügen.'
    },
    'es': {
        'name': 'Español', 'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto Perfil', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Subir CV (PDF)', 'upload_help': 'Arrastra archivo aquí', 'step2_title': '2. Oferta de Trabajo', 'job_placeholder': 'Pega la oferta aquí...', 'btn_label': 'Generar Documentos', 'spinner_msg': 'Analizando con Gemini 3 Pro...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': '¡Hecho!', 'error': 'Error', 'missing_key': 'Falta clave API.', 'missing_inputs': 'Por favor sube PDF y pega la oferta.'
    },
    'pt': {
        'name': 'Português', 'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto Perfil', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Carregar CV (PDF)', 'upload_help': 'Arraste arquivo aqui', 'step2_title': '2. Anúncio de Vaga', 'job_placeholder': 'Cole o anúncio aqui...', 'btn_label': 'Gerar Documentos', 'spinner_msg': 'Analisando com Gemini 3 Pro...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto!', 'error': 'Erro', 'missing_key': 'Chave API ausente.', 'missing_inputs': 'Por favor envie PDF e cole o anúncio.'
    }
}

# --- 4. FUNZIONI UTILITY (Backend) ---

def get_text_from_pdf(pdf_file):
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception:
        return ""

def process_image(uploaded_file, border_size):
    """Aggiunge bordo bianco e prepara per Word"""
    try:
        img = Image.open(uploaded_file)
        # Assicura RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Aggiunge bordo
        if border_size > 0:
            img = ImageOps.expand(img, border=border_size, fill='white')
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception:
        return None

def set_cell_background(cell, color_hex):
    """Colore sfondo cella Word (Hex senza #)"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def create_cv_docx(data_json, photo_bytes):
    """Crea il DOCX del CV con layout ottimizzato"""
    doc = Document()
    
    # Margini stretti
    section = doc.sections[0]
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)

    # --- BANNER SUPERIORE (Tabella 1x2) ---
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    # LAYOUT CRITICO: Colonna foto stretta, colonna testo larga
    col0_width = Inches(1.35) # Abbastanza per la foto
    col1_width = Inches(6.15) # Il resto della pagina
    
    table.columns[0].width = col0_width
    table.columns[1].width = col1_width
    
    # Altezza fissa riga (Banner)
    row = table.rows[0]
    row.height = Inches(2.0)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    
    cell_img = row.cells[0]
    cell_txt = row.cells[1]
    
    # Colore sfondo Blu Scuro (#1F4E79)
    bg_color = "1F4E79" 
    set_cell_background(cell_img, bg_color)
    set_cell_background(cell_txt, bg_color)
    
    # Inserimento Foto
    cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_img = cell_img.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Rimuovi margini paragrafo per centratura perfetta
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(0)
    
    if photo_bytes:
        run_img = p_img.add_run()
        run_img.add_picture(photo_bytes, width=Inches(1.25)) # Foto leggermente più piccola della colonna
    
    # Inserimento Testo Banner
    cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_txt = cell_txt.paragraphs[0]
    p_txt.alignment = WD_ALIGN_PARAGRAPH.LEFT # Allineato a sinistra vicino alla foto
    p_txt.paragraph_format.left_indent = Pt(10) # Piccolo rientro
    
    # Nome
    name_run = p_txt.add_run(f"{data_json.get('name', 'Name Surname').upper()}\n")
    name_run.font.name = 'Arial'
    name_run.font.size = Pt(24)
    name_run.font.color.rgb = RGBColor(255, 255, 255)
    name_run.bold = True
    
    # Dati Contatto (Address | Phone | Email)
    contact_info = f"{data_json.get('address', '')}\n{data_json.get('phone', '')} • {data_json.get('email', '')}"
    contact_run = p_txt.add_run(contact_info)
    contact_run.font.name = 'Arial'
    contact_run.font.size = Pt(10)
    contact_run.font.color.rgb = RGBColor(230, 230, 230)

    # Spazio dopo banner
    doc.add_paragraph().space_after = Pt(12)

    # --- CORPO DEL CV ---
    cv_body = data_json.get('cv_content', '')
    
    for line in cv_body.split('\n'):
        line = line.strip()
        if not line: continue
        
        # Gestione Titoli (Maiuscolo e Corto -> Titolo Sezione)
        if line.isupper() and len(line) < 50 and any(c.isalpha() for c in line):
            p = doc.add_paragraph()
            p.space_before = Pt(12)
            p.space_after = Pt(6)
            run = p.add_run(line)
            run.font.name = 'Arial'
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(31, 78, 121) # Blu scuro
            run.bold = True
            
            # Linea sotto il titolo
            p_element = p._p
            pPr = p_element.get_or_add_pPr()
            pbdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '6')
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), '1F4E79')
            pbdr.append(bottom)
            pPr.append(pbdr)
        else:
            # Testo Normale
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(2)
            run = p.runs[0]
            run.font.name = 'Calibri'
            run.font.size = Pt(11)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_letter_docx(text_content):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    for line in text_content.split('\n'):
        line = line.strip()
        if line:
            doc.add_paragraph(line)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 5. LOGICA AI (GEMINI 3.0) ---
def generate_content(cv_text, job_text, lang_name):
    try:
        # Modello Specifico Richiesto
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        prompt = f"""
        Role: Professional HR Expert & Translator.
        Task: Create a CV and Cover Letter based on the inputs.
        Target Language: {lang_name} (Strictly).
        
        INPUTS:
        1. Original CV Text: {cv_text[:30000]}
        2. Job Description: {job_text[:10000]}
        
        INSTRUCTIONS:
        1. Extract Name, Address, Phone, Email from CV for the header.
        2. Rewrite the CV body in {lang_name}. Make it professional, action-oriented, and optimized for the Job Description. DO NOT include the header info in the body text (it goes in the banner). Use UPPERCASE for section headers.
        3. Write a tailored Cover Letter in {lang_name}.
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "name": "First Last",
            "address": "Full Address",
            "phone": "+123...",
            "email": "example@mail.com",
            "cv_content": "Full rewritten CV body text...",
            "cover_letter": "Full cover letter text..."
        }}
        """
        
        response = model.generate_content(prompt)
        # Pulizia JSON
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
        
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- 6. INTERFACCIA UTENTE ---

# 6a. Configurazione Chiave
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error(TRANSLATIONS['en_us']['missing_key'])
    st.stop()

# 6b. Sidebar
with st.sidebar:
    # Selezione Lingua
    lang_keys = list(TRANSLATIONS.keys())
    # Mappa nomi per selectbox
    lang_names = [TRANSLATIONS[k]['name'] for k in lang_keys]
    
    # Trova indice corrente
    current_index = 0
    try:
        current_index = lang_keys.index(st.session_state['lang_code'])
    except: pass
    
    selected_lang_name = st.selectbox("Language / Lingua", lang_names, index=current_index)
    
    # Aggiorna session state in base alla selezione
    for k, v in TRANSLATIONS.items():
        if v['name'] == selected_lang_name:
            st.session_state['lang_code'] = k
            break
            
    t = TRANSLATIONS[st.session_state['lang_code']]
    
    st.title(t['sidebar_title'])
    
    # Foto
    st.markdown(f"**{t['photo_label']}**")
    uploaded_photo = st.file_uploader("Photo", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
    border = st.slider(t['border_label'], 0, 50, 5)
    
    if uploaded_photo:
        # Processa subito per anteprima e salvataggio
        processed_bytes = process_image(uploaded_photo, border)
        if processed_bytes:
            st.session_state['processed_photo_bytes'] = processed_bytes
            st.image(processed_bytes, caption=t['preview_label'], width=150)

# 6c. Main Page
st.title(t['main_title'])

col1, col2 = st.columns(2)

with col1:
    st.subheader(t['step1_title'])
    cv_file = st.file_uploader("CV PDF", type="pdf", label_visibility="collapsed")

with col2:
    st.subheader(t['step2_title'])
    # Text area con chiave per persistenza
    job_desc = st.text_area("Job", height=200, placeholder=t['job_placeholder'], label_visibility="collapsed")

st.markdown("---")

if st.button(t['btn_label'], type="primary", use_container_width=True):
    if cv_file and job_desc:
        with st.spinner(t['spinner_msg']):
            # 1. Estrai testo
            cv_text = get_text_from_pdf(cv_file)
            
            # 2. Chiama AI
            data = generate_content(cv_text, job_desc, t['name'])
            
            if data:
                st.session_state['generated_data'] = data
                st.success(t['success'])
            else:
                st.error(t['error'])
    else:
        st.warning(t['missing_inputs'])

# 6d. Risultati
if st.session_state['generated_data']:
    data = st.session_state['generated_data']
    
    tab1, tab2 = st.tabs([t['tab_cv'], t['tab_letter']])
    
    with tab1:
        # Genera DOCX
        cv_docx = create_cv_docx(data, st.session_state['processed_photo_bytes'])
        
        st.download_button(
            label=f"📥 {t['down_cv']}",
            data=cv_docx,
            file_name="CV_Optimized.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.text_area("Preview", value=data.get('cv_content', ''), height=500)
        
    with tab2:
        # Genera Letter DOCX
        letter_docx = create_letter_docx(data.get('cover_letter', ''))
        
        st.download_button(
            label=f"📥 {t['down_let']}",
            data=letter_docx,
            file_name="Cover_Letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.text_area("Preview", value=data.get('cover_letter', ''), height=500)
