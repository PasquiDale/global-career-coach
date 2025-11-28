import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image, ImageOps
import io
import json
import pypdf

# 1. CONFIGURAZIONE PAGINA (PRIMA ISTRUZIONE ASSOLUTA)
st.set_page_config(
    page_title="Global Career Coach",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INIZIALIZZAZIONE SESSION STATE
if 'lang_code' not in st.session_state:
    st.session_state['lang_code'] = 'it'
if 'generated_data' not in st.session_state:
    st.session_state['generated_data'] = None
if 'processed_photo' not in st.session_state:
    st.session_state['processed_photo'] = None

# 3. DIZIONARIO TRADUZIONI COMPLETO
TRANSLATIONS = {
    'it': {'sidebar_title': 'Impostazioni Profilo', 'lang_label': 'Lingua', 'photo_label': 'Foto Profilo', 'border_label': 'Bordo (px)', 'preview_label': 'Anteprima', 'main_title': 'Generatore CV Professionale', 'step1_title': '1. Carica CV (PDF)', 'upload_help': 'Trascina file qui', 'step2_title': '2. Annuncio di Lavoro', 'job_placeholder': 'Incolla qui il testo dell\'offerta...', 'btn_label': 'Genera Documenti', 'spinner_msg': 'Elaborazione in corso...', 'tab_cv': 'CV Generato', 'tab_letter': 'Lettera', 'down_cv': 'Scarica CV (Word)', 'down_let': 'Scarica Lettera (Word)', 'success': 'Fatto!', 'error': 'Errore', 'profile_header': 'PROFILO PERSONALE'},
    'en_us': {'sidebar_title': 'Profile Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Professional CV Generator', 'step1_title': '1. Upload CV (PDF)', 'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_header': 'PROFESSIONAL SUMMARY'},
    'de_ch': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Professioneller Lebenslauf-Generator', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenbeschrieb', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Motivationsschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_header': 'PERSÖNLICHES PROFIL'},
    'de_de': {'sidebar_title': 'Einstellungen', 'lang_label': 'Sprache', 'photo_label': 'Profilbild', 'border_label': 'Rahmen (px)', 'preview_label': 'Vorschau', 'main_title': 'Professioneller Lebenslauf-Generator', 'step1_title': '1. Lebenslauf hochladen (PDF)', 'upload_help': 'Datei hier ablegen', 'step2_title': '2. Stellenanzeige', 'job_placeholder': 'Stellenanzeige einfügen...', 'btn_label': 'Dokumente erstellen', 'spinner_msg': 'Verarbeitung läuft...', 'tab_cv': 'Lebenslauf', 'tab_letter': 'Anschreiben', 'down_cv': 'Lebenslauf laden', 'down_let': 'Brief laden', 'success': 'Fertig!', 'error': 'Fehler', 'profile_header': 'PERSÖNLICHES PROFIL'},
    'es': {'sidebar_title': 'Configuración', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borde (px)', 'preview_label': 'Vista previa', 'main_title': 'Generador CV Profesional', 'step1_title': '1. Subir CV', 'upload_help': 'Arrastra aquí', 'step2_title': '2. Oferta', 'job_placeholder': 'Pega la oferta...', 'btn_label': 'Generar', 'spinner_msg': 'Procesando...', 'tab_cv': 'CV Generado', 'tab_letter': 'Carta', 'down_cv': 'Descargar CV', 'down_let': 'Descargar Carta', 'success': 'Hecho', 'error': 'Error', 'profile_header': 'PERFIL PROFESIONAL'},
    'pt': {'sidebar_title': 'Configurações', 'lang_label': 'Idioma', 'photo_label': 'Foto', 'border_label': 'Borda (px)', 'preview_label': 'Visualizar', 'main_title': 'Gerador CV Profissional', 'step1_title': '1. Carregar CV', 'upload_help': 'Arraste aqui', 'step2_title': '2. Anúncio', 'job_placeholder': 'Cole o anúncio...', 'btn_label': 'Gerar', 'spinner_msg': 'Processando...', 'tab_cv': 'CV Gerado', 'tab_letter': 'Carta', 'down_cv': 'Baixar CV', 'down_let': 'Baixar Carta', 'success': 'Pronto', 'error': 'Erro', 'profile_header': 'PERFIL PROFISSIONAL'},
    'en_uk': {'sidebar_title': 'Settings', 'lang_label': 'Language', 'photo_label': 'Profile Photo', 'border_label': 'Border (px)', 'preview_label': 'Preview', 'main_title': 'Professional CV Generator', 'step1_title': '1. Upload CV', 'upload_help': 'Drop file here', 'step2_title': '2. Job Description', 'job_placeholder': 'Paste job offer...', 'btn_label': 'Generate Documents', 'spinner_msg': 'Processing...', 'tab_cv': 'Generated CV', 'tab_letter': 'Cover Letter', 'down_cv': 'Download CV', 'down_let': 'Download Letter', 'success': 'Done!', 'error': 'Error', 'profile_header': 'PROFESSIONAL PROFILE'}
}

# 4. FUNZIONI HELPER

def set_cell_background(cell, color_hex):
    """Imposta il colore di sfondo di una cella Word."""
    cell_properties = cell._element.get_or_add_tcPr()
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:val'), 'clear')
    shading_elm.set(qn('w:color'), 'auto')
    shading_elm.set(qn('w:fill'), color_hex)
    cell_properties.append(shading_elm)

def process_image(image_file, border_width):
    """Aggiunge bordo bianco all'immagine."""
    if image_file:
        img = Image.open(image_file)
        if border_width > 0:
            img = ImageOps.expand(img, border=border_width, fill='white')
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr
    return None

def create_docx(json_data, photo_bytes, lang_code):
    """Crea il file Word con layout specifico: Header Blu, Foto a Sx centrata, Profilo."""
    doc = Document()
    
    # Margini pagina
    section = doc.sections[0]
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    # 1. CREAZIONE BANNER BLU (Tabella 1 riga, 2 colonne)
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False 
    
    # Dimensioni Colonne
    # La larghezza totale è circa 7.1 pollici.
    # Colonna Foto molto stretta per eliminare spazio a sinistra
    table.columns[0].width = Inches(1.2)
    table.columns[1].width = Inches(6.1)
    
    row = table.rows[0]
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    row.height = Inches(2.0) # Altezza fissa
    
    cell_photo = row.cells[0]
    cell_text = row.cells[1]
    
    # Sfondo Blu (#1F4E79)
    set_cell_background(cell_photo, "1F4E79")
    set_cell_background(cell_text, "1F4E79")
    
    # CRUCIALE: Allineamento Verticale Cella
    cell_photo.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    cell_text.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    
    # 2. INSERIMENTO FOTO
    if photo_bytes:
        paragraph = cell_photo.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT # Foto tutto a sinistra
        
        # Reset margini paragrafo per centratura perfetta nella cella
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        
        run = paragraph.add_run()
        run.add_picture(photo_bytes, width=Inches(1.2)) # Larghezza uguale alla colonna
    
    # 3. INSERIMENTO TESTO HEADER (Nome e Contatti)
    paragraph = cell_text.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.left_indent = Pt(10) # Leggero rientro dal bordo foto
    
    # Nome
    name = json_data.get('personal_info', {}).get('name', '')
    run_name = paragraph.add_run(name + "\n")
    run_name.font.name = 'Arial'
    run_name.font.size = Pt(24)
    run_name.font.color.rgb = RGBColor(255, 255, 255)
    run_name.bold = True
    
    # Contatti
    contact_info = json_data.get('personal_info', {}).get('contact_details', [])
    for contact in contact_info:
        run_contact = paragraph.add_run(contact + "\n")
        run_contact.font.name = 'Arial'
        run_contact.font.size = Pt(11)
        run_contact.font.color.rgb = RGBColor(255, 255, 255)

    doc.add_paragraph("") # Spazio

    # 4. SEZIONE PROFILO PERSONALE (Subito dopo header)
    profile_text = json_data.get('profile_summary', '')
    if profile_text:
        # Titolo Profilo
        p_title = doc.add_paragraph()
        run_title = p_title.add_run(TRANSLATIONS[lang_code]['profile_header'])
        run_title.font.name = 'Arial'
        run_title.font.size = Pt(12)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(31, 78, 121)
        
        # Linea sotto titolo
        p_element = p_title._p
        pPr = p_element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '4')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), 'auto')
        pBdr.append(bottom)
        pPr.append(pBdr)

        # Testo Profilo
        p_body = doc.add_paragraph(profile_text)
        p_body.paragraph_format.space_after = Pt(12)

    # 5. RESTO DEL CV (Esperienza, Istruzione, etc.)
    # Il resto arriva come testo grezzo formattato dall'AI, lo parsiamo
    body_text = json_data.get('cv_body', '')
    
    for line in body_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Rilevamento Titoli Sezioni (es. ESPERIENZA)
        if len(line) < 50 and line.isupper() and any(c.isalpha() for c in line):
            p = doc.add_paragraph()
            p.space_before = Pt(12)
            p.space_after = Pt(3)
            run = p.add_run(line)
            run.font.name = 'Arial'
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(31, 78, 121)
            
            # Linea sotto
            p_element = p._p
            pPr = p_element.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '4')
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), 'auto')
            pBdr.append(bottom)
            pPr.append(pBdr)
            
        elif line.startswith("-") or line.startswith("•"):
            p = doc.add_paragraph(line.lstrip("-• "), style='List Bullet')
            p.paragraph_format.space_after = Pt(2)
        else:
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(2)
            run = p.runs[0]
            run.font.name = 'Calibri'
            run.font.size = Pt(11)

    docx_file = io.BytesIO()
    doc.save(docx_file)
    docx_file.seek(0)
    return docx_file

def create_letter_docx(text):
    """Crea documento Word per la lettera."""
    doc = Document()
    for line in text.split('\n'):
        if line.strip():
            doc.add_paragraph(line.strip())
    
    docx_file = io.BytesIO()
    doc.save(docx_file)
    docx_file.seek(0)
    return docx_file

# 5. GENERAZIONE CONTENUTI (GEMINI)
def generate_content(pdf_text, job_text, lang_key):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        target_lang = {
            'it': 'Italian', 'en_us': 'English (US)', 'de_ch': 'German (Swiss)', 
            'de_de': 'German (Germany)', 'es': 'Spanish', 'pt': 'Portuguese', 'en_uk': 'English (UK)'
        }.get(lang_key, 'English')

        prompt = f"""
        You are a professional HR Resume Writer. 
        Output STRICTLY JSON. No Markdown. No Intro.
        Target Language: {target_lang}.
        
        INPUT:
        1. Original CV Text: {pdf_text}
        2. Job Description: {job_text}
        
        TASK:
        1. Extract Name and Contact Details.
        2. Write a strong "Professional Summary/Profile" tailored to the job.
        3. Rewrite the rest of the CV (Experience, Education, Skills) improving clarity. Use Uppercase for Section Titles.
        4. Write a Cover Letter.
        
        JSON STRUCTURE:
        {{
            "personal_info": {{
                "name": "Full Name",
                "contact_details": ["Address", "Phone", "Email", "LinkedIn"]
            }},
            "profile_summary": "The professional summary text...",
            "cv_body": "The rest of the CV text (Experience, Education...) with Uppercase headers...",
            "cover_letter_text": "Full text of the cover letter..."
        }}
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# 6. MAIN LOOP DELL'APPLICAZIONE
def main():
    # SIDEBAR
    with st.sidebar:
        t = TRANSLATIONS[st.session_state['lang_code']]
        st.title(t['sidebar_title'])
        
        lang_options = list(TRANSLATIONS.keys())
        selected_lang = st.selectbox(
            t['lang_label'], 
            options=lang_options, 
            index=lang_options.index(st.session_state['lang_code'])
        )
        if selected_lang != st.session_state['lang_code']:
            st.session_state['lang_code'] = selected_lang
            st.rerun()
            
        st.divider()
        
        st.subheader(t['photo_label'])
        uploaded_photo = st.file_uploader(" ", type=['jpg', 'jpeg', 'png'])
        border_width = st.slider(t['border_label'], 0, 50, 5)
        
        if uploaded_photo:
            st.session_state['processed_photo'] = process_image(uploaded_photo, border_width)
            st.image(st.session_state['processed_photo'], caption=t['preview_label'])

    # MAIN CONTENT
    t = TRANSLATIONS[st.session_state['lang_code']]
    st.title(t['main_title'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(t['step1_title'])
        uploaded_cv = st.file_uploader(t['upload_help'], type=['pdf'])
        
    with col2:
        st.subheader(t['step2_title'])
        job_desc = st.text_area(t['job_placeholder'], height=200)

    if st.button(t['btn_label'], type="primary", use_container_width=True):
        if uploaded_cv and job_desc:
            with st.spinner(t['spinner_msg']):
                reader = pypdf.PdfReader(uploaded_cv)
                pdf_text = ""
                for page in reader.pages:
                    pdf_text += page.extract_text() + "\n"
                
                result = generate_content(pdf_text, job_desc, st.session_state['lang_code'])
                
                if result:
                    st.session_state['generated_data'] = result
                    st.success(t['success'])
        else:
            st.warning("Carica PDF e inserisci Annuncio.")

    if st.session_state['generated_data']:
        st.divider()
        data = st.session_state['generated_data']
        
        tab1, tab2 = st.tabs([t['tab_cv'], t['tab_letter']])
        
        with tab1:
            # Mostra anteprima del profilo + corpo
            preview_text = f"**{t['profile_header']}**\n\n{data.get('profile_summary', '')}\n\n{data.get('cv_body', '')}"
            st.text_area("", value=preview_text, height=500)
            
            docx_cv = create_docx(data, st.session_state['processed_photo'], st.session_state['lang_code'])
            st.download_button(
                t['down_cv'], 
                data=docx_cv, 
                file_name="CV_Optimized.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        with tab2:
            st.text_area("", value=data.get('cover_letter_text', ''), height=500)
            docx_let = create_letter_docx(data.get('cover_letter_text', ''))
            st.download_button(
                t['down_let'], 
                data=docx_let, 
                file_name="Cover_Letter.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

if __name__ == "__main__":
    main()
