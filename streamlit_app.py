import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import json
import pypdf
import re
import base64
from PIL import Image, ImageOps

# --- 1. CONFIGURAZIONE PAGINA E STATO ---
st.set_page_config(
    page_title="Global Career AI",
    page_icon="🌍",
    layout="wide"
)

# Inizializzazione Stato
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "cv_text_extracted" not in st.session_state:
    st.session_state.cv_text_extracted = ""
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None

# --- 2. CONFIGURAZIONE API ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 CRITICAL ERROR: GEMINI_API_KEY missing in secrets.")
    st.stop()

# --- 3. FUNZIONI UTILITY GRAFICHE ---

def get_image_base64(image_file):
    """Converte un file immagine caricato in stringa base64 per HTML."""
    if image_file is not None:
        try:
            # Resetta il puntatore del file se è stato già letto
            image_file.seek(0)
            bytes_data = image_file.read()
            return base64.b64encode(bytes_data).decode()
        except Exception:
            return None
    return None

def set_cell_background(cell, color_hex):
    """Imposta il colore di sfondo di una cella in Word (XML hack)."""
    cell_properties = cell._element.get_or_add_tcPr()
    shading_element = OxmlElement('w:shd')
    shading_element.set(qn('w:val'), 'clear')
    shading_element.set(qn('w:color'), 'auto')
    shading_element.set(qn('w:fill'), color_hex)
    cell_properties.append(shading_element)

def clean_markdown_for_word(text):
    """Pulisce il testo dai simboli Markdown."""
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#+\s', '', text)
    return text.strip()

def extract_text_from_pdf(uploaded_file):
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

# --- 4. MOTORE AI ---

def get_gemini_response(cv_text, job_desc, lang_code):
    try:
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        # Istruzioni lingua
        lang_map = {
            "it": "Italian", "en_uk": "British English", "en_us": "American English",
            "de_de": "German", "de_ch": "Swiss German (no 'ß')", "es": "Spanish", "pt": "Portuguese"
        }
        target_lang = lang_map.get(lang_code, "English")
        
        prompt = f"""
        You are a Senior Design & Career Consultant.
        Target Language: {target_lang}.
        
        [INPUT CV]: {cv_text}
        [JOB DESCRIPTION]: {job_desc}
        
        [TASK]:
        1. Extract Name and Contact Info accurately.
        2. Rewrite the CV body to be professional and tailored to the job.
        3. Write a Cover Letter.
        
        [JSON OUTPUT FORMAT]:
        {{
            "personal_info": {{
                "name": "First Lastname",
                "contact_line": "City, Country | Phone | Email"
            }},
            "cv_body_markdown": "Professional profile, Experience, Education... Use ### for Section Titles.",
            "cover_letter_text": "Dear Hiring Manager..."
        }}
        """
        
        response = model.generate_content(prompt)
        text_resp = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text_resp)
        
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- 5. GENERAZIONE WORD AVANZATA ---

def create_styled_docx(data, photo_file, border_width):
    doc = Document()
    
    # Margini
    section = doc.sections[0]
    section.top_margin = Cm(1.5)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    
    # --- HEADER BLU (TABELLA) ---
    # Creiamo una tabella 1 riga, 2 colonne per Foto + Testo
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    
    # Larghezza colonne (Foto piccola, Testo largo)
    table.columns[0].width = Cm(4.0)
    table.columns[1].width = Cm(13.0)
    
    cell_photo = table.cell(0, 0)
    cell_info = table.cell(0, 1)
    
    # Sfondo Blu (#20547d)
    set_cell_background(cell_photo, "20547d")
    set_cell_background(cell_info, "20547d")
    
    # Inserimento Foto (se presente)
    cell_photo.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if photo_file:
        try:
            # Riapriamo il file per PIL
            photo_file.seek(0)
            img = Image.open(photo_file)
            
            # Aggiungiamo il bordo bianco con PIL prima di mettere in Word
            # Convertiamo px slider in pixel reali (approssimazione)
            border_px = int(border_width * 2) 
            if border_px > 0:
                img = ImageOps.expand(img, border=border_px, fill='white')
            
            # Salvataggio temporaneo in memoria
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format if img.format else 'PNG')
            img_byte_arr.seek(0)
            
            p = cell_photo.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(img_byte_arr, width=Cm(3.5))
        except:
            pass # Se la foto fallisce, lasciamo vuoto
            
    # Inserimento Testo Header
    cell_info.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p_name = cell_info.paragraphs[0]
    run_name = p_name.add_run(data['personal_info']['name'])
    run_name.font.size = Pt(24)
    run_name.font.color.rgb = RGBColor(255, 255, 255) # Bianco
    run_name.bold = True
    
    p_contact = cell_info.add_paragraph(data['personal_info']['contact_line'])
    run_contact = p_contact.runs[0]
    run_contact.font.size = Pt(10)
    run_contact.font.color.rgb = RGBColor(230, 230, 230) # Bianco sporco
    
    # Spazio dopo header
    doc.add_paragraph().space_after = Pt(12)
    
    # --- CORPO CV ---
    body_text = clean_markdown_for_word(data['cv_body_markdown'])
    
    for line in body_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        # Rilevamento Titoli (Logica semplice: Maiuscolo o ###)
        # Qui usiamo il blu scuro per i titoli
        if line.isupper() and len(line) < 50:
            p = doc.add_paragraph()
            p.space_before = Pt(12)
            run = p.add_run(line)
            run.bold = True
            run.font.size = Pt(12)
            run.font.color.rgb = RGBColor(32, 84, 125) # Blu #20547d
            
            # Linea sotto (Border bottom è complesso in python-docx puro senza XML hack lunghi, 
            # usiamo un carattere di sottolineatura grafico come fallback o lasciamo solo colore)
        else:
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(2)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_simple_docx(text):
    """Per la lettera di presentazione (layout standard)."""
    doc = Document()
    clean = clean_markdown_for_word(text)
    for line in clean.split('\n'):
        if line.strip():
            doc.add_paragraph(line.strip())
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 6. INTERFACCIA (UI) ---

# DIZIONARIO LINGUE (Semplificato per brevità, espandibile)
LANGS = {
    "Italiano": "it", "English (UK)": "en_uk", "English (US)": "en_us",
    "Deutsch (DE)": "de_de", "Deutsch (CH)": "de_ch", "Español": "es", "Português": "pt"
}

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Impostazioni")
    selected_lang = st.selectbox("Lingua / Language", list(LANGS.keys()))
    lang_code = LANGS[selected_lang]
    
    st.markdown("---")
    st.subheader("Foto Profilo")
    uploaded_photo = st.file_uploader("Carica Foto", type=['jpg', 'png', 'jpeg'])
    border_width = st.slider("Spessore Bordo Bianco", 0, 20, 5)
    
    # Preview Sidebar (Semplice)
    if uploaded_photo:
        st.image(uploaded_photo, width=150, caption="Foto Caricata")

# --- MAIN PAGE ---
st.title("🎨 Global Career AI")
st.markdown(f"Generazione CV Professionale in **{selected_lang}**")

col1, col2 = st.columns(2)
with col1:
    uploaded_cv = st.file_uploader("1. Carica il tuo CV (PDF)", type="pdf")
with col2:
    st.text_area("2. Annuncio di Lavoro", height=150, key="job_description")

# --- BOTTONE ---
if st.button("✨ Genera CV & Lettera", type="primary", use_container_width=True):
    if not uploaded_cv or not st.session_state.job_description:
        st.warning("⚠️ Carica CV e inserisci Annuncio.")
    else:
        with st.spinner("Analisi e Design in corso..."):
            # Estrazione Testo
            cv_text = extract_text_from_pdf(uploaded_cv)
            
            if cv_text:
                # Chiamata AI
                data = get_gemini_response(cv_text, st.session_state.job_description, lang_code)
                
                if data:
                    st.session_state.generated_content = data
                    st.success("Fatto!")

# --- OUTPUT RISULTATI ---
if st.session_state.generated_content:
    data = st.session_state.generated_content
    
    tab_cv, tab_cl = st.tabs(["📄 CV Grafico", "✉️ Lettera"])
    
    # --- TAB 1: ANTEPRIMA GRAFICA CV ---
    with tab_cv:
        # Recupero dati per HTML
        name = data['personal_info']['name']
        contact = data['personal_info']['contact_line']
        body = clean_markdown_for_word(data['cv_body_markdown']).replace("\n", "<br>")
        
        # Gestione immagine Base64 per HTML
        img_tag = ""
        if uploaded_photo:
            b64_str = get_image_base64(uploaded_photo)
            if b64_str:
                # CSS per il bordo bianco
                img_tag = f'<img src="data:image/png;base64,{b64_str}" style="width:120px; height:120px; object-fit:cover; border-radius:50%; border: {border_width}px solid white; margin-right:20px;">'
        
        # HTML/CSS PER ANTEPRIMA REALISTICA
        html_preview = f"""
        <div style="font-family: Arial, sans-serif; border: 1px solid #ddd; max-width: 800px; margin: auto;">
            <!-- HEADER BLU -->
            <div style="background-color: #20547d; color: white; padding: 30px; display: flex; align-items: center;">
                {img_tag}
                <div>
                    <h1 style="margin: 0; font-size: 32px; text-transform: uppercase;">{name}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">{contact}</p>
                </div>
            </div>
            <!-- CORPO -->
            <div style="padding: 30px; color: #333; line-height: 1.6;">
                {body}
            </div>
        </div>
        """
        
        st.markdown(html_preview, unsafe_allow_html=True)
        
        # Bottone Download Word (Generato con layout tabellare)
        docx_cv = create_styled_docx(data, uploaded_photo, border_width)
        st.download_button(
            "⬇️ Scarica CV in Word (Design Blu)",
            data=docx_cv,
            file_name=f"CV_{name.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # --- TAB 2: LETTERA ---
    with tab_cl:
        st.markdown(data['cover_letter_text'])
        
        docx_cl = create_simple_docx(data['cover_letter_text'])
        st.download_button(
            "⬇️ Scarica Lettera (.docx)",
            data=docx_cl,
            file_name="Cover_Letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
