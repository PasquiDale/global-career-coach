import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import json
import pypdf
from PIL import Image, ImageOps

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None
if 'processed_photo_bytes' not in st.session_state:
    st.session_state['processed_photo_bytes'] = None

# --- 3. DIZIONARIO TRADUZIONI (NO RIFERIMENTI AI/GEMINI) ---
TRANSLATIONS = {
    'it': {
        'name': 'Italiano', 'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 
        'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima Foto', 
        'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Carica il tuo CV (PDF)', 
        'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 
        'job_placeholder': 'Incolla qui il testo dell\'offerta di lavoro...', 'btn_label': 'Genera Documenti', 
        'spinner_msg': 'Elaborazione e scrittura professionale in corso...', # GENERICO
        'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 
        'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 
        'success': 'Documenti pronti!', 'error': 'Si è verificato un errore', 
        'missing_key': 'Licenza non attiva.', 'missing_inputs': 'Caricare PDF e Annuncio.'
    },
    'en_us': {
        'name': 'English (US)', 'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 
        'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Photo Preview', 
        'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Upload CV (PDF)', 
        'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 
        'job_placeholder': 'Paste job offer text here...', 'btn_label': 'Generate Documents', 
        'spinner_msg': 'Processing and writing documents...', # GENERICO
        'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 
        'down_cv': 'Download CV', 'down_let': 'Download Letter', 
        'success': 'Ready!', 'error': 'Error', 
        'missing_key': 'License key missing.', 'missing_inputs': 'Please upload inputs.'
    },
    'de_ch': {
        'name': 'Deutsch (CH)', 'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 
        'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 
        'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Lebenslauf hochladen (PDF)', 
        'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenbeschrieb', 
        'job_placeholder': 'Stellenanzeige hier einfügen...', 'btn_label': 'Dokumente erstellen', 
        'spinner_msg': 'Verarbeitung und Erstellung laufen...', # GENERICO
        'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 
        'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 
        'success': 'Fertig!', 'error': 'Fehler', 
        'missing_key': 'Lizenzschlüssel fehlt.', 'missing_inputs': 'Bitte Eingaben prüfen.'
    },
    'de_de': {
        'name': 'Deutsch (DE)', 'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 
        'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 
        'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Lebenslauf hochladen (PDF)', 
        'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 
        'job_placeholder': 'Stellenanzeige hier einfügen...', 'btn_label': 'Dokumente erstellen', 
        'spinner_msg': 'Verarbeitung und Erstellung laufen...', # GENERICO
        'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 
        'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 
        'success': 'Fertig!', 'error': 'Fehler', 
        'missing_key': 'Lizenzschlüssel fehlt.', 'missing_inputs': 'Bitte Eingaben prüfen.'
    },
    'es': {
        'name': 'Español', 'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 
        'photo_label': 'Foto Perfil', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 
        'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Subir CV (PDF)', 
        'upload_help': 'Arrastra archivo aquí', 'step2_title': '2. Oferta de Trabajo', 
        'job_placeholder': 'Pega la oferta aquí...', 'btn_label': 'Generar Documentos', 
        'spinner_msg': 'Procesando documentos...', # GENERICO
        'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 
        'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 
        'success': '¡Listo!', 'error': 'Error', 
        'missing_key': 'Falta licencia.', 'missing_inputs': 'Faltan datos.'
    },
    'pt': {
        'name': 'Português', 'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 
        'photo_label': 'Foto Perfil', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 
        'main_title': 'Global Career Coach 🚀', 'step1_title': '1. Carregar CV (PDF)', 
        'upload_help': 'Arraste arquivo aqui', 'step2_title': '2. Anúncio de Vaga', 
        'job_placeholder': 'Cole o anúncio aqui...', 'btn_label': 'Gerar Documentos', 
        'spinner_msg': 'Processando documentos...', # GENERICO
        'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 
        'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 
        'success': 'Pronto!', 'error': 'Erro', 
        'missing_key': 'Chave ausente.', 'missing_inputs': 'Dados ausentes.'
    }
}

# --- 4. FUNZIONI UTILITY ---

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
    try:
        img = Image.open(uploaded_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        if border_size > 0:
            img = ImageOps.expand(img, border=border_size, fill='white')
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception:
        return None

def set_cell_background(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def create_cv_docx(data_json, photo_bytes):
    doc = Document()
    
    section = doc.sections[0]
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)

    # --- BANNER ---
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    col0_width = Inches(1.3)
    col1_width = Inches(6.2)
    
    table.columns[0].width = col0_width
    table.columns[1].width = col1_width
    
    row = table.rows[0]
    row.height = Inches(2.0)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    
    cell_img = row.cells[0]
    cell_txt = row.cells[1]
    
    bg_color = "1F4E79"
    set_cell_background(cell_img, bg_color)
    set_cell_background(cell_txt, bg_color)
    
    # --- FOTO (Centratura Verticale Fix) ---
    cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_img = cell_img.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Rimuoviamo spaziatura paragrafo per centratura matematica
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(0)
    
    if photo_bytes:
        run_img = p_img.add_run()
        run_img.add_picture(photo_bytes, width=Inches(1.25))
    
    # --- TESTO ---
    cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_txt = cell_txt.paragraphs[0]
    p_txt.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_txt.paragraph_format.left_indent = Pt(10)
    p_txt.paragraph_format.space_before = Pt(0) # Fix allineamento
    p_txt.paragraph_format.space_after = Pt(0)  # Fix allineamento
    
    name_run = p_txt.add_run(f"{data_json.get('name', '').upper()}\n")
    name_run.font.name = 'Arial'
    name_run.font.size = Pt(24)
    name_run.font.color.rgb = RGBColor(255, 255, 255)
    name_run.bold = True
    
    contact_info = f"{data_json.get('address', '')}\n{data_json.get('phone', '')} • {data_json.get('email', '')}"
    contact_run = p_txt.add_run(contact_info)
    contact_run.font.name = 'Arial'
    contact_run.font.size = Pt(10)
    contact_run.font.color.rgb = RGBColor(230, 230, 230)

    doc.add_paragraph().space_after = Pt(12)

    # --- BODY ---
    cv_body = data_json.get('cv_content', '')
    for line in cv_body.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.isupper() and len(line) < 50 and any(c.isalpha() for c in line):
            p = doc.add_paragraph()
            p.space_before = Pt(12)
            p.space_after = Pt(6)
            run = p.add_run(line)
            run.font.name = 'Arial'
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(31, 78, 121)
            run.bold = True
            
            p_elm = p._p
            pPr = p_elm.get_or_add_pPr()
            pbdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '6')
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), '1F4E79')
            pbdr.append(bottom)
            pPr.append(pbdr)
        else:
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
        if line: doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 5. LOGICA AI ---
def generate_content(cv_text, job_text, lang_name):
    try:
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        prompt = f"""
        Role: HR Expert.
        Target Language: {lang_name}.
        INPUTS: CV: {cv_text[:30000]} | Job: {job_text[:10000]}
        INSTRUCTIONS:
        1. Extract Name, Address, Phone, Email.
        2. Rewrite CV body in {lang_name} (UPPERCASE headers). NO header info in body.
        3. Write Cover Letter in {lang_name}.
        OUTPUT JSON:
        {{
            "name": "...", "address": "...", "phone": "...", "email": "...",
            "cv_content": "...", "cover_letter": "..."
        }}
        """
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        return None

# --- 6. INTERFACCIA ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("License Key Error.")
    st.stop()

with st.sidebar:
    lang_keys = list(TRANSLATIONS.keys())
    lang_names = [TRANSLATIONS[k]['name'] for k in lang_keys]
    
    curr_idx = 0
    if st.session_state['lang_code'] in lang_keys:
        curr_idx = lang_keys.index(st.session_state['lang_code'])
        
    sel_name = st.selectbox("Language", lang_names, index=curr_idx)
    
    for k, v in TRANSLATIONS.items():
        if v['name'] == sel_name:
            st.session_state['lang_code'] = k
            break
    
    t = TRANSLATIONS[st.session_state['lang_code']]
    st.title(t['sidebar_title'])
    
    st.markdown(f"**{t['photo_label']}**")
    up_photo = st.file_uploader("Photo", type=['jpg','png','jpeg'], label_visibility="collapsed")
    border = st.slider(t['border_label'], 0, 50, 5)
    
    if up_photo:
        proc_bytes = process_image(up_photo, border)
        if proc_bytes:
            st.session_state['processed_photo_bytes'] = proc_bytes
            st.image(proc_bytes, caption=t['preview_label'], width=150)

st.title(t['main_title'])
c1, c2 = st.columns(2)
with c1:
    st.subheader(t['step1_title'])
    cv_file = st.file_uploader("CV", type="pdf", label_visibility="collapsed")
with c2:
    st.subheader(t['step2_title'])
    job_desc = st.text_area("Job", height=200, placeholder=t['job_placeholder'], label_visibility="collapsed")

st.markdown("---")

if st.button(t['btn_label'], type="primary", use_container_width=True):
    if cv_file and job_desc:
        with st.spinner(t['spinner_msg']):
            cv_txt = get_text_from_pdf(cv_file)
            data = generate_content(cv_txt, job_desc, t['name'])
            if data:
                st.session_state['generated_data'] = data
                st.success(t['success'])
            else:
                st.error(t['error'])
    else:
        st.warning(t['missing_inputs'])

if st.session_state['generated_data']:
    data = st.session_state['generated_data']
    tab1, tab2 = st.tabs([t['tab_cv'], t['tab_letter']])
    
    with tab1:
        cv_docx = create_cv_docx(data, st.session_state['processed_photo_bytes'])
        st.download_button(label=f"📥 {t['down_cv']}", data=cv_docx, file_name="CV.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.text_area("Preview", value=data.get('cv_content',''), height=500)
        
    with tab2:
        let_docx = create_letter_docx(data.get('cover_letter',''))
        st.download_button(label=f"📥 {t['down_let']}", data=let_docx, file_name="Letter.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.text_area("Preview", value=data.get('cover_letter',''), height=500)
