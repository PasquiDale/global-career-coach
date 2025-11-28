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

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state.lang_code = 'it'
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'processed_photo' not in st.session_state:
    st.session_state.processed_photo = None

# --- 3. COSTANTI E DIZIONARI ---

LANG_DISPLAY = {
    "Italiano": "it",
    "English (US)": "en_us",
    "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

# Traduzioni interfaccia
TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Generatore CV Professionale', 'step1_title': '1. Carica CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'missing_key': 'Chiave API mancante'},
    'en_us': {'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Professional CV Generator', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'missing_key': 'Missing API Key'},
    'de_de': {'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Professioneller Lebenslauf-Generator', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Professioneller Lebenslauf-Generator', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenbeschrieb', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt'},
    'es': {'sidebar_title': 'Configuración', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Generador CV Profesional', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'missing_key': 'Falta clave API'},
    'pt': {'sidebar_title': 'Configurações', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Gerador CV Profissional', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'missing_key': 'Chave API ausente'},
    'en_uk': {'sidebar_title': 'Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Professional CV Generator', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'missing_key': 'Missing API Key'}
}

# Titoli Sezioni forzati per lingua
SECTION_TITLES = {
    'it': {'experience': 'ESPERIENZA PROFESSIONALE', 'education': 'ISTRUZIONE E FORMAZIONE', 'skills': 'COMPETENZE', 'profile_summary': 'PROFILO PERSONALE', 'languages': 'LINGUE'},
    'de_ch': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE & FÄHIGKEITEN', 'profile_summary': 'PERSÖNLICHES PROFIL', 'languages': 'SPRACHEN'},
    'de_de': {'experience': 'BERUFSERFAHRUNG', 'education': 'AUSBILDUNG', 'skills': 'KENNTNISSE', 'profile_summary': 'PERSÖNLICHES PROFIL', 'languages': 'SPRACHEN'},
    'en_us': {'experience': 'PROFESSIONAL EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'profile_summary': 'PROFESSIONAL PROFILE', 'languages': 'LANGUAGES'},
    'en_uk': {'experience': 'WORK EXPERIENCE', 'education': 'EDUCATION', 'skills': 'SKILLS', 'profile_summary': 'PROFESSIONAL PROFILE', 'languages': 'LANGUAGES'},
    'es': {'experience': 'EXPERIENCIA LABORAL', 'education': 'EDUCACIÓN', 'skills': 'HABILIDADES', 'profile_summary': 'PERFIL PROFESIONAL', 'languages': 'IDIOMAS'},
    'pt': {'experience': 'EXPERIÊNCIA PROFISSIONAL', 'education': 'EDUCAÇÃO', 'skills': 'COMPETÊNCIAS', 'profile_summary': 'PERFIL PROFISSIONAL', 'languages': 'IDIOMAS'}
}

# --- 4. FUNZIONI HELPER ---

def set_table_background(table, color_hex):
    """Imposta lo sfondo dell'intera tabella tramite XML."""
    tblPr = table._tblPr
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tblPr.append(shd)

def add_bottom_border(paragraph):
    """Aggiunge una linea orizzontale blu sotto il paragrafo."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')      # Spessore linea
    bottom.set(qn('w:space'), '1')   # Spaziatura
    bottom.set(qn('w:color'), '20547D') # Colore Blu Scuro
    pbdr.append(bottom)
    pPr.append(pbdr)

def process_image(image_file, border_width):
    """Aggiunge bordo bianco alla foto."""
    img = Image.open(image_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return ImageOps.expand(img, border=border_width, fill='white')

def clean_text(text):
    if not text: return ""
    return text.replace("**", "").replace("##", "").strip()

def create_docx(data, photo_stream, lang_code):
    """Crea il file Word con layout banner preciso e titoli tradotti."""
    doc = Document()
    
    # 1. Impostazione Margini
    section = doc.sections[0]
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.5)
    
    # --- HEADER BANNER (Tabella 1x2 - Sfondo Blu Scuro) ---
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    # Colore Sfondo Header (#20547d)
    set_table_background(table, "20547D")
    
    # Dimensioni Colonne
    col0_width = Inches(1.5)
    col1_width = Inches(6.0)
    table.columns[0].width = col0_width
    table.columns[1].width = col1_width
    
    # Altezza Riga Fissa
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    row.height = Inches(2.0)
    
    cell_foto = row.cells[0]
    cell_text = row.cells[1]
    
    # --- FOTO (SINISTRA) ---
    cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if photo_stream:
        p_foto = cell_foto.paragraphs[0]
        p_foto.alignment = WD_ALIGN_PARAGRAPH.LEFT 
        p_foto.paragraph_format.space_before = Pt(0)
        p_foto.paragraph_format.space_after = Pt(0)
        p_foto.paragraph_format.left_indent = Pt(10) 
        run_foto = p_foto.add_run()
        run_foto.add_picture(photo_stream, height=Inches(1.5))
    
    # --- TESTO INTESTAZIONE (DESTRA) ---
    cell_text.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # Nome
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
    
    # Contatti
    p_info = cell_text.add_paragraph()
    p_info.paragraph_format.space_before = Pt(6)
    p_info.paragraph_format.space_after = Pt(0)
    
    contact_str = f"{clean_text(info.get('address', ''))}\n{clean_text(info.get('phone', ''))} | {clean_text(info.get('email', ''))}"
    run_info = p_info.add_run(contact_str)
    run_info.font.size = Pt(10)
    run_info.font.color.rgb = RGBColor(220, 220, 220)
    run_info.font.name = 'Arial'

    # Spazio dopo banner
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # --- BODY (Con titoli corretti e linee) ---
    
    # Carichiamo i titoli nella lingua corretta
    titles = SECTION_TITLES.get(lang_code, SECTION_TITLES['en_us'])

    # 1. PROFILO (Se presente)
    if data.get('profile_summary'):
        h = doc.add_heading(titles.get('profile_summary', 'PROFILE'), level=1)
        h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
        h.runs[0].font.name = 'Arial'
        h.runs[0].font.size = Pt(12)
        h.runs[0].bold = True
        add_bottom_border(h) # LINEA SOTTO
        
        p = doc.add_paragraph(clean_text(data.get('profile_summary')))
        p.paragraph_format.space_after = Pt(12)

    # 2. ALTRE SEZIONI (Ordine forzato)
    sections_to_print = ['experience', 'education', 'skills', 'languages']
    
    for key in sections_to_print:
        content = data.get(key)
        if content:
            # Titolo Sezione Tradotto
            title_text = titles.get(key, key.upper())
            
            h = doc.add_heading(title_text, level=1)
            h.runs[0].font.color.rgb = RGBColor(32, 84, 125)
            h.runs[0].font.name = 'Arial'
            h.runs[0].font.size = Pt(12)
            h.runs[0].bold = True
            add_bottom_border(h) # LINEA SOTTO
            
            # Contenuto
            if isinstance(content, list):
                for item in content:
                    p = doc.add_paragraph(clean_text(str(item)), style='List Bullet')
            else:
                doc.add_paragraph(clean_text(str(content)))
            
            doc.add_paragraph().paragraph_format.space_after = Pt(8) # Spazio tra sezioni

    # Salvataggio
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_letter_docx(text):
    doc = Document()
    for paragraph in clean_text(text).split('\n'):
        if paragraph.strip():
            doc.add_paragraph(paragraph.strip())
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 5. MAIN APP ---

def main():
    # Sidebar
    lang_name = st.sidebar.selectbox("Lingua / Language", list(LANG_DISPLAY.keys()))
    lang_code = LANG_DISPLAY[lang_name]
    st.session_state.lang_code = lang_code
    t = TRANSLATIONS[lang_code]
    
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
                    reader = pypdf.PdfReader(cv_file)
                    text = ""
                    for p in reader.pages: text += p.extract_text() + "\n"
                    
                    model = genai.GenerativeModel("models/gemini-3-pro-preview")
                    
                    # Prompt Ottimizzato
                    prompt = f"""
                    Role: Professional HR Resume Writer.
                    Language: {lang_name}.
                    
                    Task: 
                    1. Extract candidate personal info.
                    2. Write a 'profile_summary'.
                    3. Rewrite experience, education, skills, languages professionally.
                    4. Write a cover_letter.
                    
                    INPUT CV: {text[:30000]}
                    INPUT JOB: {job_desc}
                    
                    OUTPUT JSON format strictly:
                    {{
                        "personal_info": {{ "first_name": "...", "last_name": "...", "email": "...", "phone": "...", "address": "..." }},
                        "profile_summary": "...",
                        "experience": ["...", "..."],
                        "education": ["...", "..."],
                        "skills": ["...", "..."],
                        "languages": ["..."],
                        "cover_letter": "..."
                    }}
                    """
                    
                    response = model.generate_content(prompt)
                    json_str = response.text.replace("```json", "").replace("```", "").strip()
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
                
            docx = create_docx(data, img_stream, lang_code)
            
            st.download_button(
                label=f"📥 {t['down_cv']}",
                data=docx,
                file_name="CV_Optimized.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.json(data)
            
        with tab2:
            letter = data.get('cover_letter', '')
            docx_l = create_letter_docx(letter)
            
            st.download_button(
                label=f"📥 {t['down_let']}",
                data=docx_l,
                file_name="Cover_Letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.markdown(letter)

if __name__ == "__main__":
    main()
