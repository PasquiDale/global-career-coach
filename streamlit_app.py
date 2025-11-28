import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
from PIL import Image, ImageOps
import pypdf
import json

# --- 1. CONFIGURAZIONE PAGINA (PRIMA ISTRUZIONE) ---
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
if 'raw_text' not in st.session_state:
    st.session_state.raw_text = ""

# --- 3. COSTANTI E DIZIONARI ---

# Mappa per visualizzazione lingua -> codice interno
LANG_DISPLAY = {
    "Italiano": "it",
    "English (US)": "en_us",
    "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

# Dizionario traduzioni completo
TRANSLATIONS = {
    'it': {
        'sidebar_title': 'Impostazioni Profilo', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 
        'preview_label': 'Anteprima', 'main_title': 'Generatore CV Professionale', 'step1_title': '1. Carica CV (PDF)', 
        'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 
        'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 
        'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 
        'success': 'Fatto!', 'error': 'Errore', 'missing_key': 'Chiave API mancante', 'missing_data': 'Carica CV e Annuncio'
    },
    'en_us': {
        'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 
        'preview_label': 'Preview', 'main_title': 'Professional CV Generator', 'step1_title': '1. Upload CV (PDF)', 
        'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer...', 
        'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 
        'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 
        'success': 'Done!', 'error': 'Error', 'missing_key': 'Missing API Key', 'missing_data': 'Upload CV and Job Desc'
    },
    'en_uk': {
        'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 
        'preview_label': 'Preview', 'main_title': 'Professional CV Generator', 'step1_title': '1. Upload CV (PDF)', 
        'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer...', 
        'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 
        'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 
        'success': 'Done!', 'error': 'Error', 'missing_key': 'Missing API Key', 'missing_data': 'Upload CV and Job Desc'
    },
    'de_de': {
        'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 
        'preview_label': 'Vorschau', 'main_title': 'Professioneller Lebenslauf-Generator', 'step1_title': '1. Lebenslauf hochladen (PDF)', 
        'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 
        'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 
        'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 
        'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt', 'missing_data': 'CV und Anzeige hochladen'
    },
    'de_ch': {
        'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 
        'preview_label': 'Vorschau', 'main_title': 'Professioneller Lebenslauf-Generator', 'step1_title': '1. Lebenslauf hochladen (PDF)', 
        'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenbeschrieb', 'job_placeholder': 'Stellenanzeige einfügen...', 
        'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 
        'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 
        'success': 'Fertig!', 'error': 'Fehler', 'missing_key': 'API-Schlüssel fehlt', 'missing_data': 'CV und Anzeige hochladen'
    },
    'es': {
        'sidebar_title': 'Configuración', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 
        'preview_label': 'Vista previa', 'main_title': 'Generador CV Profesional', 'step1_title': '1. Subir CV', 
        'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta', 'job_placeholder': 'Pega la oferta...', 
        'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 
        'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 
        'success': 'Hecho', 'error': 'Error', 'missing_key': 'Falta clave API', 'missing_data': 'Subir CV y Oferta'
    },
    'pt': {
        'sidebar_title': 'Configurações', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 
        'preview_label': 'Visualizar', 'main_title': 'Gerador CV Profissional', 'step1_title': '1. Carregar CV', 
        'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio', 'job_placeholder': 'Cole o anúncio...', 
        'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 
        'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 
        'success': 'Pronto', 'error': 'Erro', 'missing_key': 'Chave API ausente', 'missing_data': 'Carregar CV e Anúncio'
    }
}

# --- 4. FUNZIONI HELPER ---

def set_table_background(table, color_hex):
    """Imposta il colore di sfondo per l'intera tabella (Banner)."""
    tblPr = table._tblPr
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tblPr.append(shd)

def process_image(image_file, border_width):
    """Aggiunge il bordo bianco alla foto."""
    img = Image.open(image_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return ImageOps.expand(img, border=border_width, fill='white')

def clean_text(text):
    """Pulisce il testo da markdown."""
    if not text: return ""
    return text.replace("**", "").replace("##", "").replace("###", "").strip()

def create_docx(data, photo_stream):
    """
    Crea un file Word con allineamento PIXEL-PERFECT tra foto e testo.
    """
    doc = Document()
    
    # 1. Impostazione Margini (Stretti per il banner)
    section = doc.sections[0]
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.5)
    
    # 2. Creazione Tabella Banner (1 Riga, 2 Colonne)
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False # Fondamentale per controllare le larghezze
    
    # Sfondo Blu Scuro
    set_table_background(table, "1F4E79")
    
    # 3. Impostazione Dimensioni Rigide
    # Larghezza totale pagina (8.5) - Margini (1.0) = 7.5 inches disponibili
    col0_width = Inches(1.8) # Colonna Foto
    col1_width = Inches(5.7) # Colonna Testo
    
    table.columns[0].width = col0_width
    table.columns[1].width = col1_width
    
    # Altezza Riga fissa per garantire l'allineamento verticale
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    row.height = Inches(2.2) # Altezza sufficiente per foto e testo
    
    # --- CELLA SINISTRA: FOTO ---
    cell_foto = row.cells[0]
    cell_foto.width = col0_width
    cell_foto.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    if photo_stream:
        p_foto = cell_foto.paragraphs[0]
        p_foto.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Rimuove spaziature parassite
        p_foto.paragraph_format.space_before = Pt(0)
        p_foto.paragraph_format.space_after = Pt(0)
        run_foto = p_foto.add_run()
        run_foto.add_picture(photo_stream, height=Inches(1.6))
        
    # --- CELLA DESTRA: TESTO ---
    cell_text = row.cells[1]
    cell_text.width = col1_width
    cell_text.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # Nome (Titolo Grande)
    p_name = cell_text.paragraphs[0]
    p_name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    # CRUCIALE: Rimuovere spazi per allineamento matematico
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(0)
    p_name.paragraph_format.line_spacing = 1.0 
    
    run_name = p_name.add_run(clean_text(data.get('name', 'Nome Cognome')))
    run_name.font.size = Pt(26)
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    run_name.font.name = 'Arial'
    run_name.bold = True
    
    # Contatti (Sotto il nome)
    p_info = cell_text.add_paragraph()
    p_info.paragraph_format.space_before = Pt(6) # Piccolo distacco dal nome
    p_info.paragraph_format.space_after = Pt(0)
    
    contact_str = f"{data.get('address', '')} | {data.get('phone', '')} | {data.get('email', '')}"
    run_info = p_info.add_run(clean_text(contact_str))
    run_info.font.size = Pt(10)
    run_info.font.color.rgb = RGBColor(220, 220, 220)
    run_info.font.name = 'Arial'

    # Spazio dopo banner
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # --- SEZIONE PROFILO ---
    if data.get('profile_summary'):
        h_prof = doc.add_heading('PROFILO', level=1)
        h_prof.runs[0].font.color.rgb = RGBColor(31, 78, 121)
        p_prof = doc.add_paragraph(clean_text(data.get('profile_summary')))
        p_prof.paragraph_format.space_after = Pt(12)

    # --- CORPO DEL CV ---
    body_text = clean_text(data.get('cv_content', ''))
    for line in body_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        # Rilevamento titoli (Maiuscolo e corto)
        if len(line) < 50 and line.isupper() and any(c.isalpha() for c in line) and "@" not in line:
            p = doc.add_heading(line, level=1)
            p.runs[0].font.color.rgb = RGBColor(31, 78, 121)
            p.runs[0].font.size = Pt(12)
        else:
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(2)

    # Salvataggio
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_letter_docx(text):
    """Crea documento Word per la lettera."""
    doc = Document()
    for line in clean_text(text).split('\n'):
        if line.strip():
            doc.add_paragraph(line.strip())
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 5. MAIN APPLICATION ---

def main():
    # Gestione Lingua
    selected_lang_name = st.sidebar.selectbox("Lingua / Language", list(LANG_DISPLAY.keys()))
    st.session_state.lang_code = LANG_DISPLAY[selected_lang_name]
    t = TRANSLATIONS[st.session_state.lang_code]
    
    st.title(t['main_title'])
    
    # Gestione API Key
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception:
        st.error("🚨 " + t.get('missing_key', 'API Key Error'))
        st.stop()

    # --- SIDEBAR (FOTO) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader(t['sidebar_title'])
    
    uploaded_photo = st.sidebar.file_uploader(t['photo_label'], type=['jpg', 'png', 'jpeg'])
    border_width = st.sidebar.slider(t['border_label'], 0, 20, 5)
    
    if uploaded_photo:
        processed_img = process_image(uploaded_photo, border_width)
        st.session_state.processed_photo = processed_img
        
        # Anteprima
        st.sidebar.markdown(f"**{t['preview_label']}**")
        st.sidebar.image(processed_img, width=150)
    
    # --- MAIN CONTENT ---
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
            st.error(t['missing_data'])
        else:
            with st.spinner(t['spinner_msg']):
                try:
                    # 1. Estrazione Testo PDF
                    reader = pypdf.PdfReader(cv_file)
                    raw_text = ""
                    for page in reader.pages:
                        raw_text += page.extract_text() + "\n"
                    
                    # 2. Chiamata AI (GEMINI 3 PRO PREVIEW)
                    # Forziamo il modello richiesto
                    model = genai.GenerativeModel("models/gemini-3-pro-preview")
                    
                    prompt = f"""
                    You are a professional HR Expert.
                    Language: {selected_lang_name}.
                    
                    TASK:
                    1. Extract candidate data (name, email, phone, address).
                    2. Write a professional profile summary (3-4 lines).
                    3. Rewrite the CV content professionally (Action-Oriented).
                    4. Write a Cover Letter tailored to the Job Description.
                    
                    INPUT CV:
                    {raw_text[:20000]}
                    
                    INPUT JOB:
                    {job_desc}
                    
                    OUTPUT FORMAT (JSON ONLY):
                    {{
                        "name": "...",
                        "email": "...",
                        "phone": "...",
                        "address": "...",
                        "profile_summary": "...",
                        "cv_content": "...structured text without contact info...",
                        "cover_letter": "...text..."
                    }}
                    """
                    
                    response = model.generate_content(prompt)
                    
                    # Pulizia JSON
                    json_str = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(json_str)
                    st.session_state.generated_data = data
                    st.success(t['success'])
                    
                except Exception as e:
                    st.error(f"{t['error']}: {str(e)}")

    # --- OUTPUT ---
    if st.session_state.generated_data:
        data = st.session_state.generated_data
        
        tab1, tab2 = st.tabs([t['tab_cv'], t['tab_letter']])
        
        with tab1:
            # Preparazione Foto per Word
            img_stream = None
            if st.session_state.processed_photo:
                img_stream = io.BytesIO()
                st.session_state.processed_photo.save(img_stream, format='JPEG')
                img_stream.seek(0)
            
            # Generazione Word
            docx_file = create_docx(data, img_stream)
            
            st.download_button(
                label=f"📥 {t['down_cv']}",
                data=docx_file,
                file_name=f"CV_{data.get('name', 'Professional').replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            st.markdown("### Preview")
            st.write(data.get('cv_content'))

        with tab2:
            letter_text = data.get('cover_letter', '')
            docx_letter = create_letter_docx(letter_text)
            
            st.download_button(
                label=f"📥 {t['down_let']}",
                data=docx_letter,
                file_name="Cover_Letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.markdown("### Preview")
            st.write(letter_text)

if __name__ == "__main__":
    main()
