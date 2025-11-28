import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml
import io
import json
import pypdf
import re
from PIL import Image, ImageOps
from datetime import datetime
import locale

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS CUSTOM ---
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    div[data-testid="stFileUploader"] { margin-bottom: 1rem; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; }
    .success-box { padding: 1rem; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 1rem; }
    /* Nascondere menu standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. INIZIALIZZAZIONE SESSION STATE ---
if 'lang_code' not in st.session_state:
    st.session_state.lang_code = 'it'
if 'generated_data' not in st.session_state:
    st.session_state.generated_data = None
if 'processed_photo' not in st.session_state:
    st.session_state.processed_photo = None

# --- 4. COSTANTI E DIZIONARI ---

LANG_DISPLAY = {
    "Italiano": "it",
    "English (US)": "en_us",
    "English (UK)": "en_uk",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Français": "fr",
    "Español": "es",
    "Português": "pt"
}

TRANSLATIONS = {
    'it': {
        'sidebar_title': 'Impostazioni Profilo', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 
        'preview_label': 'Anteprima', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carica CV (PDF)', 
        'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 
        'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 
        'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 
        'success': 'Fatto!', 'error': 'Errore', 'profile_title': 'PROFILO PERSONALE'
    },
    'en_us': {
        'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 
        'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV (PDF)', 
        'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 
        'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 
        'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 
        'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE'
    },
    'en_uk': {
        'sidebar_title': 'Profile Settings', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 
        'preview_label': 'Preview', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Upload CV', 
        'upload_help': 'Drop file here', 'step2_title': '2. Job Advertisement', 'job_placeholder': 'Paste job offer...', 
        'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 
        'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 
        'success': 'Done!', 'error': 'Error', 'profile_title': 'PROFESSIONAL PROFILE'
    },
    'de_ch': {
        'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 
        'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 
        'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stelleninserat', 'job_placeholder': 'Stelleninserat hier einfügen...', 
        'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 
        'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 
        'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL'
    },
    'de_de': {
        'sidebar_title': 'Einstellungen', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 
        'preview_label': 'Vorschau', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Lebenslauf hochladen (PDF)', 
        'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 
        'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 
        'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 
        'success': 'Fertig!', 'error': 'Fehler', 'profile_title': 'PERSÖNLICHES PROFIL'
    },
    'fr': {
        'sidebar_title': 'Paramètres du Profil', 'photo_label': 'Photo de Profil', 'border_label': 'Bordure (px)', 
        'preview_label': 'Aperçu', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Télécharger CV (PDF)', 
        'upload_help': 'Déposez le fichier ici', 'step2_title': '2. Offre d\'Emploi', 'job_placeholder': 'Collez le texte de l\'offre ici...', 
        'btn_label': 'Générer Documents', 'spinner_msg': 'Traitement en cours...', 'tab_cv': 'CV Généré', 
        'tab_letter': 'Lettre', 'down_cv': 'Télécharger CV (Word)', 'down_let': 'Télécharger Lettre (Word)', 
        'success': 'Terminé!', 'error': 'Erreur', 'profile_title': 'PROFIL PROFESSIONNEL'
    },
    'es': {
        'sidebar_title': 'Configuración', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 
        'preview_label': 'Vista previa', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Subir CV', 
        'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta de Empleo', 'job_placeholder': 'Pega la oferta...', 
        'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 
        'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 
        'success': 'Hecho', 'error': 'Error', 'profile_title': 'PERFIL PROFESIONAL'
    },
    'pt': {
        'sidebar_title': 'Configurações', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 
        'preview_label': 'Visualizar', 'main_title': 'Global Career Coach 🌍', 'step1_title': '1. Carregar CV', 
        'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio de Emprego', 'job_placeholder': 'Cole o anúncio...', 
        'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 
        'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 
        'success': 'Pronto', 'error': 'Erro', 'profile_title': 'PERFIL PROFISSIONAL'
    }
}

SECTION_TITLES = {
    'it': ["ESPERIENZA PROFESSIONALE", "ISTRUZIONE E FORMAZIONE", "COMPETENZE LINGUISTICHE", "COMPETENZE TECNICHE", "HOBBY E INTERESSI", "REFERENZE", "PROFILO PERSONALE"],
    'en_us': ["PROFESSIONAL EXPERIENCE", "EDUCATION", "LANGUAGES", "TECHNICAL SKILLS", "HOBBIES & INTERESTS", "REFERENCES", "PROFESSIONAL PROFILE"],
    'en_uk': ["PROFESSIONAL EXPERIENCE", "EDUCATION", "LANGUAGES", "TECHNICAL SKILLS", "HOBBIES & INTERESTS", "REFERENCES", "PROFESSIONAL PROFILE"],
    'de_ch': ["BERUFSERFAHRUNG", "AUSBILDUNG", "SPRACHKENNTNISSE", "IT-KENNTNISSE", "INTERESSEN", "REFERENZEN", "PERSÖNLICHES PROFIL"],
    'de_de': ["BERUFLICHER WERDEGANG", "AUSBILDUNG", "SPRACHKENNTNISSE", "EDV-KENNTNISSE", "INTERESSEN", "REFERENZEN", "PERSÖNLICHES PROFIL"],
    'fr': ["EXPÉRIENCE PROFESSIONNELLE", "FORMATION", "LANGUES", "COMPÉTENCES TECHNIQUES", "CENTRES D'INTÉRÊT", "RÉFÉRENCES", "PROFIL PROFESSIONNEL"],
    'es': ["EXPERIENCIA PROFESIONAL", "EDUCACIÓN", "IDIOMAS", "HABILIDADES TÉCNICAS", "INTERESES", "REFERENCIAS", "PERFIL PROFESIONAL"],
    'pt': ["EXPERIÊNCIA PROFISSIONAL", "EDUCAÇÃO", "IDIOMAS", "COMPETÊNCIAS TÉCNICAS", "INTERESSES", "REFERÊNCIAS", "PERFIL PROFISSIONAL"]
}

# --- 5. FUNZIONI HELPER ---

def get_todays_date(lang_code):
    """Genera la data corrente formattata in base alla lingua."""
    now = datetime.now()
    if lang_code in ['de_ch', 'de_de', 'it', 'fr', 'pt', 'es']:
        return now.strftime("%d.%m.%Y")
    elif lang_code in ['en_us', 'en_uk']:
        return now.strftime("%B %d, %Y")
    return now.strftime("%Y-%m-%d")

def set_table_background(table, color_hex):
    """Imposta lo sfondo blu scuro per l'header del CV."""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    for row in table.rows:
        for cell in row.cells:
            if cell._tc.get_or_add_tcPr().find(qn('w:shd')) is None:
                cell._tc.get_or_add_tcPr().append(shading_elm)

def add_bottom_border(paragraph):
    """Aggiunge una linea orizzontale sotto il paragrafo (per i titoli)."""
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '4')  # 1/2 pt
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'auto')
    pbdr.append(bottom)
    pPr.append(pbdr)

def process_image(uploaded_file, border_width):
    """Elabora la foto aggiungendo il bordo bianco."""
    if not uploaded_file:
        return None
    try:
        img = Image.open(uploaded_file).convert("RGB")
        if border_width > 0:
            img = ImageOps.expand(img, border=border_width, fill='white')
        return img
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None

def extract_text_from_pdf(pdf_file):
    """Estrae testo puro dal PDF."""
    try:
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
        return ""

# --- 6. FUNZIONI DI GENERAZIONE WORD (CORE) ---

def create_cv_docx(json_data, photo_img, lang_code):
    """Crea il file Word del CV con layout fisso (Banner Blu, Foto SX)."""
    doc = Document()
    
    # Margini
    section = doc.sections[0]
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    # Stili
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(11)

    # --- HEADER (BANNER BLU) ---
    header_table = doc.add_table(rows=1, cols=2)
    header_table.autofit = False
    header_table.allow_autofit = False
    
    # Larghezza colonne
    header_table.columns[0].width = Cm(5.0)  # Colonna Foto
    header_table.columns[1].width = Cm(11.5) # Colonna Testo
    
    # Colore Sfondo Header #1F4E79
    set_table_background(header_table, "1F4E79")
    
    # Cella 1: Foto
    cell_photo = header_table.cell(0, 0)
    cell_photo.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if photo_img:
        img_buffer = io.BytesIO()
        photo_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        p = cell_photo.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(img_buffer, width=Cm(4.0))
    else:
        # Se non c'è foto, lascia vuoto o metti placeholder
        pass

    # Cella 2: Dati Personali
    cell_info = header_table.cell(0, 1)
    cell_info.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    p_info = cell_info.paragraphs[0]
    p_info.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Nome e Cognome (Grande, Bianco)
    pi = json_data.get('personal_info', {})
    name_run = p_info.add_run(f"{pi.get('name', '')}\n")
    name_run.font.name = 'Calibri'
    name_run.font.size = Pt(24)
    name_run.font.color.rgb = RGBColor(255, 255, 255)
    name_run.bold = True
    
    # Spazio
    p_info.add_run("\n")
    
    # Dati contatto (Bianco)
    contact_text = f"{pi.get('address', '')} | {pi.get('phone', '')} | {pi.get('email', '')}\n{pi.get('linkedin', '')}"
    info_run = p_info.add_run(contact_text)
    info_run.font.name = 'Calibri'
    info_run.font.size = Pt(10)
    info_run.font.color.rgb = RGBColor(255, 255, 255)

    doc.add_paragraph().space_after = Pt(12)

    # --- SEZIONI CV ---
    sections = json_data.get('cv_sections', [])
    
    # Definiamo titoli noti per evidenziare
    known_titles = SECTION_TITLES.get(lang_code, [])
    
    for sec in sections:
        title = sec.get('title', '').strip()
        content = sec.get('content', '')
        
        # Titolo Sezione (Blu scuro #1F4E79, All Caps, Riga sotto)
        h = doc.add_paragraph()
        add_bottom_border(h)
        run_h = h.add_run(title.upper())
        run_h.font.name = 'Calibri'
        run_h.font.size = Pt(12)
        run_h.font.color.rgb = RGBColor(31, 78, 121)
        run_h.bold = True
        h.space_before = Pt(12)
        h.space_after = Pt(6)
        
        # Contenuto (Proiettili o testo)
        if isinstance(content, list):
            for item in content:
                p = doc.add_paragraph(style='List Bullet')
                p.paragraph_format.space_after = Pt(2)
                run_p = p.add_run(str(item))
        else:
            p = doc.add_paragraph(str(content))
            p.paragraph_format.space_after = Pt(6)

    # Output
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_letter_docx(json_data, lang_code, candidate_name):
    """Crea la Lettera di Presentazione con data reale e firma indivisibile."""
    doc = Document()
    
    # Margini
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(11)

    ld = json_data.get('letter_data', {})

    # 1. Mittente (Opzionale, spesso in alto a dx o sx)
    # Per semplicità, standard block style
    
    # 2. Destinatario
    rec = ld.get('recipient_block', '')
    if rec:
        p_rec = doc.add_paragraph(rec)
        p_rec.space_after = Pt(12)

    # 3. DATA REALE (Allineata a Sinistra o Destra secondo standard, usiamo SX per semplicità)
    real_date = get_todays_date(lang_code)
    # A seconda della lingua, a volte si mette luogo prima (es. "Zürich, den 28.11.2025")
    # Qui mettiamo solo la data per sicurezza universale
    p_date = doc.add_paragraph(real_date)
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT # Standard business spesso a destra
    p_date.space_after = Pt(18)

    # 4. Oggetto
    subj = ld.get('subject_line', '')
    if subj:
        p_subj = doc.add_paragraph()
        run_subj = p_subj.add_run(subj)
        run_subj.bold = True
        p_subj.space_after = Pt(12)

    # 5. Corpo
    body = ld.get('body_content', '')
    # Puliamo markdown se presente
    body = body.replace('**', '').replace('#', '')
    
    for para in body.split('\n'):
        if para.strip():
            p = doc.add_paragraph(para.strip())
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15

    doc.add_paragraph().space_after = Pt(12)

    # 6. FIRMA INDIVISIBILE (Keep with next)
    closing = ld.get('closing', 'Freundliche Grüsse') # Fallback
    
    # Paragrafo Saluti
    p_close = doc.add_paragraph(closing)
    p_close.paragraph_format.keep_with_next = True
    p_close.space_after = Pt(0) # Spazio gestito dai paragrafi vuoti

    # Spazio firma (3-4 righe vuote)
    for _ in range(3):
        p_space = doc.add_paragraph()
        p_space.paragraph_format.keep_with_next = True
        p_space.space_after = Pt(0)

    # Nome Candidato
    p_sign = doc.add_paragraph(candidate_name)
    # Non serve keep_with_next qui, è l'ultimo elemento del blocco

    # Output
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 7. SIDEBAR E UI PRINCIPALE ---

# Sidebar
with st.sidebar:
    lang_sel = st.selectbox("Language / Lingua", list(LANG_DISPLAY.keys()))
    st.session_state.lang_code = LANG_DISPLAY[lang_sel]
    t = TRANSLATIONS[st.session_state.lang_code]
    
    st.title(t['sidebar_title'])
    st.markdown("---")
    
    # Upload Foto
    st.subheader(t['photo_label'])
    uploaded_photo = st.file_uploader(t['photo_label'], type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")
    
    # Slider Bordo
    border_width = st.slider(t['border_label'], 0, 20, 0)
    
    # Elaborazione e Anteprima Foto
    if uploaded_photo:
        processed_img = process_image(uploaded_photo, border_width)
        st.session_state.processed_photo = processed_img
        st.markdown(f"**{t['preview_label']}**")
        st.image(processed_img, width=150)
    else:
        st.session_state.processed_photo = None

# Main Content
st.title(t['main_title'])

# Controllo API Key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("🚨 API Key mancante nei Secrets!")
    st.stop()

# Layout a due colonne per Input
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(t['step1_title'])
    uploaded_cv = st.file_uploader(t['step1_title'], type=['pdf'], label_visibility="collapsed")

with col2:
    st.subheader(t['step2_title'])
    job_desc = st.text_area(t['step2_title'], height=200, placeholder=t['job_placeholder'], label_visibility="collapsed")

# Bottone Generazione
if st.button(t['btn_label'], type="primary"):
    if not uploaded_cv or not job_desc:
        st.warning("Per favore carica sia il CV che l'annuncio.")
    else:
        with st.spinner(t['spinner_msg']):
            try:
                # 1. Estrazione Testo CV
                cv_text = extract_text_from_pdf(uploaded_cv)
                
                # 2. Chiamata AI
                model = genai.GenerativeModel("models/gemini-3-pro-preview") # MODELLO OBBLIGATORIO
                
                prompt = f"""
                Act as an expert HR Resume Writer and Career Coach.
                Target Language: {lang_sel} ({st.session_state.lang_code}).
                
                INPUT:
                1. RESUME TEXT: {cv_text}
                2. JOB DESCRIPTION: {job_desc}
                
                TASK:
                Analyze the Resume and Job Description. Create two documents:
                A. An optimized CV structure.
                B. A tailored Cover Letter.
                
                OUTPUT FORMAT (JSON ONLY):
                {{
                    "personal_info": {{
                        "name": "Full Name",
                        "address": "Full Address",
                        "phone": "Phone Number",
                        "email": "Email",
                        "linkedin": "LinkedIn URL (optional)"
                    }},
                    "cv_sections": [
                        {{
                            "title": "Section Title (e.g., EXPERIENCE) in {st.session_state.lang_code}",
                            "content": "Content text or list of strings"
                        }}
                        ... (Profile, Experience, Education, Skills, Languages, etc.)
                    ],
                    "letter_data": {{
                        "recipient_block": "Recipient Name/Company\nAddress",
                        "subject_line": "Subject: Application for...",
                        "body_content": "Full body of the letter (multiple paragraphs).",
                        "closing": "Closing greeting (e.g., Freundliche Grüsse)"
                    }}
                }}
                
                IMPORTANT:
                - Do NOT include the Date in the JSON (I will add it programmatically).
                - Do NOT include the Candidate Name in the closing (I will add it programmatically).
                - Ensure the tone is professional and matches the target language cultural norms.
                - Optimize CV content for ATS based on Job Description keywords.
                """
                
                response = model.generate_content(prompt)
                
                # Pulizia JSON
                json_str = response.text.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:-3]
                
                data = json.loads(json_str)
                st.session_state.generated_data = data
                st.success(t['success'])
                
            except Exception as e:
                st.error(f"{t['error']}: {str(e)}")

# Visualizzazione Risultati
if st.session_state.generated_data:
    data = st.session_state.generated_data
    tabs = st.tabs([t['tab_cv'], t['tab_letter']])
    
    # TAB CV
    with tabs[0]:
        # Genera Word CV
        # Nota: usiamo st.session_state.processed_photo se esiste
        docx_cv = create_cv_docx(data, st.session_state.processed_photo, st.session_state.lang_code)
        
        st.download_button(
            label=t['down_cv'],
            data=docx_cv,
            file_name=f"CV_{data['personal_info'].get('name', 'Optimized').replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Preview JSON (Debug/Info)
        st.json(data['cv_sections'])

    # TAB LETTERA
    with tabs[1]:
        # Genera Word Lettera
        candidate_name = data['personal_info'].get('name', 'Candidate')
        docx_let = create_letter_docx(data, st.session_state.lang_code, candidate_name)
        
        st.download_button(
            label=t['down_let'],
            data=docx_let,
            file_name=f"Cover_Letter_{candidate_name.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Anteprima Testo
        ld = data.get('letter_data', {})
        st.markdown(f"**{ld.get('subject_line', '')}**")
        st.write(ld.get('body_content', ''))
        st.write(ld.get('closing', ''))
