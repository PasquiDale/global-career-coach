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

# --- 1. SETUP & CONFIGURAZIONE ---
st.set_page_config(page_title="Global Career AI", page_icon="👔", layout="wide")

# CSS per nascondere elementi standard e stilizzare l'anteprima
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
</style>
""", unsafe_allow_html=True)

# Inizializzazione Session State
if "generated_data" not in st.session_state:
    st.session_state.generated_data = None
if "job_description" not in st.session_state:
    st.session_state.job_description = ""

# --- 2. GESTIONE API KEY ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 CRITICAL: GEMINI_API_KEY mancante nei secrets.")
    st.stop()

# --- 3. HELPER FUNCTIONS GRAFICHE (WORD/DOCX) ---

def set_cell_bg(cell, color_hex):
    """Hack XML per colorare lo sfondo di una cella in Word."""
    cell_properties = cell._element.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:val'), 'clear')
    shading.set(qn('w:color'), 'auto')
    shading.set(qn('w:fill'), color_hex)
    cell_properties.append(shading)

def add_section_header(doc, text):
    """Crea un titolo di sezione Blu, Maiuscolo e con Linea Sotto."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    
    # Testo
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(32, 84, 125) # Blu #20547d
    
    # Linea Sotto (XML Hack)
    p_element = p._p
    pPr = p_element.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')      # Spessore
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '20547d') # Colore linea
    pbdr.append(bottom)
    pPr.append(pbdr)

def get_image_base64(uploaded_file, border_width):
    """Processa l'immagine e restituisce base64 per HTML."""
    if uploaded_file is None:
        return None
    try:
        image = Image.open(uploaded_file)
        # Aggiunge bordo bianco
        if border_width > 0:
            image = ImageOps.expand(image, border=border_width, fill='white')
        
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except:
        return None

def extract_pdf_text(file):
    try:
        reader = pypdf.PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except: return ""

# --- 4. LOGICA AI (JSON STRICT MODE) ---

def get_ai_data(cv_text, job_desc, lang):
    try:
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        prompt = f"""
        You are an expert HR Resume Designer.
        Target Language: {lang}.
        
        INPUT CV: {cv_text[:20000]}
        JOB DESCRIPTION: {job_desc}
        
        TASK:
        Extract and restructure the CV data to perfectly match the job description.
        Also write a Cover Letter.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "personal_info": {{
                "name": "Full Name",
                "contact_line": "Address | Phone | Email"
            }},
            "profile_summary": "A strong professional summary (3-4 lines)...",
            "experience": [
                {{"role": "Job Title", "company": "Company Name", "period": "Dates", "description": "Key achievements..."}}
            ],
            "education": [
                {{"degree": "Degree Name", "institution": "University/School", "year": "Year"}}
            ],
            "skills": ["Skill 1", "Skill 2", "Skill 3", "Skill 4", "Skill 5"],
            "cover_letter_text": "Full text of the cover letter..."
        }}
        """
        
        response = model.generate_content(prompt)
        # Pulizia JSON
        json_str = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
        
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- 5. INTERFACCIA (UI) ---

# Sidebar
with st.sidebar:
    st.title("⚙️ Configurazione")
    lang_options = ["Italiano", "English (UK)", "English (US)", "Deutsch (DE)", "Deutsch (CH)", "Español", "Português"]
    selected_lang = st.selectbox("Lingua Documenti", lang_options)
    
    st.divider()
    st.subheader("Foto Profilo")
    uploaded_photo = st.file_uploader("Carica Foto", type=['jpg', 'png', 'jpeg'])
    border_width = st.slider("Spessore Bordo", 0, 20, 8)
    
    if uploaded_photo:
        st.image(uploaded_photo, width=150)

# Main
st.title("🎨 Global Career AI")
st.caption("Professional CV Generator • Powered by **Gemini 3 Pro**")

c1, c2 = st.columns(2)
with c1:
    cv_file = st.file_uploader("1. Carica CV (PDF)", type="pdf")
with c2:
    st.text_area("2. Annuncio di Lavoro", height=100, key="job_description", placeholder="Incolla qui l'offerta...")

if st.button("✨ Genera CV & Lettera", type="primary", use_container_width=True):
    if not cv_file or not st.session_state.job_description:
        st.warning("⚠️ Carica sia il CV che l'Annuncio.")
    else:
        with st.spinner("Analisi e Design in corso..."):
            extracted_text = extract_pdf_text(cv_file)
            data = get_ai_data(extracted_text, st.session_state.job_description, selected_lang)
            
            if data:
                st.session_state.generated_data = data
                st.success("Generazione completata!")

# --- 6. VISUALIZZAZIONE & DOWNLOAD ---

if st.session_state.generated_data:
    data = st.session_state.generated_data
    
    tab_cv, tab_cl = st.tabs(["📄 CV Grafico", "✉️ Lettera"])
    
    # --- TAB CV ---
    with tab_cv:
        # Costruzione Anteprima HTML
        img_html = ""
        if uploaded_photo:
            b64 = get_image_base64(uploaded_photo, border_width)
            if b64:
                img_html = f'<img src="data:image/png;base64,{b64}" style="width:110px; height:110px; border-radius:50%; object-fit:cover; margin-right:20px;">'
        
        # HTML Layout
        html_preview = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; border: 1px solid #ddd; max-width: 850px; margin: auto; background: white;">
            <!-- HEADER BLU -->
            <div style="background-color: #20547d; color: white; padding: 25px; display: flex; align-items: center;">
                {img_html}
                <div>
                    <h1 style="margin: 0; font-size: 28px; text-transform: uppercase; letter-spacing: 1px;">{data['personal_info']['name']}</h1>
                    <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">{data['personal_info']['contact_line']}</p>
                </div>
            </div>
            
            <!-- BODY -->
            <div style="padding: 30px; color: #333;">
                <p style="font-style: italic; color: #555;">{data['profile_summary']}</p>
                
                <h3 style="color: #20547d; border-bottom: 2px solid #20547d; padding-bottom: 5px; margin-top: 20px;">ESPERIENZA</h3>
                {''.join([f"<div style='margin-bottom:15px;'><strong>{exp['role']}</strong> | {exp['company']}<br><small style='color:#666'>{exp['period']}</small><br>{exp['description']}</div>" for exp in data['experience']])}
                
                <h3 style="color: #20547d; border-bottom: 2px solid #20547d; padding-bottom: 5px; margin-top: 20px;">FORMAZIONE</h3>
                {''.join([f"<div style='margin-bottom:10px;'><strong>{edu['degree']}</strong> - {edu['institution']} ({edu['year']})</div>" for edu in data['education']])}
                
                <h3 style="color: #20547d; border-bottom: 2px solid #20547d; padding-bottom: 5px; margin-top: 20px;">SKILLS</h3>
                <p>{', '.join(data['skills'])}</p>
            </div>
        </div>
        """
        st.markdown(html_preview, unsafe_allow_html=True)
        
        # --- GENERAZIONE WORD (.docx) ---
        def create_cv_docx(data_json, photo_upl, border_w):
            doc = Document()
            # Margini
            section = doc.sections[0]
            section.top_margin = Cm(1.27)
            section.left_margin = Cm(1.27)
            section.right_margin = Cm(1.27)
            
            # --- HEADER (Tabella) ---
            table = doc.add_table(rows=1, cols=2)
            table.autofit = False
            table.columns[0].width = Cm(4.5)
            table.columns[1].width = Cm(13.0)
            
            cell_img = table.cell(0, 0)
            cell_txt = table.cell(0, 1)
            
            # Sfondo Blu (#20547d)
            set_cell_bg(cell_img, "20547d")
            set_cell_bg(cell_txt, "20547d")
            
            # Foto
            cell_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if photo_upl:
                try:
                    photo_upl.seek(0)
                    pil_img = Image.open(photo_upl)
                    # Bordo
                    if border_w > 0:
                        pil_img = ImageOps.expand(pil_img, border=int(border_w*2), fill='white')
                    
                    img_byte = io.BytesIO()
                    pil_img.save(img_byte, format="PNG")
                    img_byte.seek(0)
                    
                    p = cell_img.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(img_byte, width=Cm(3.5))
                except: pass
            
            # Testo Header
            cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p_name = cell_txt.paragraphs[0]
            r_name = p_name.add_run(data_json['personal_info']['name'])
            r_name.font.size = Pt(24)
            r_name.font.color.rgb = RGBColor(255, 255, 255)
            r_name.bold = True
            
            p_cont = cell_txt.add_paragraph(data_json['personal_info']['contact_line'])
            r_cont = p_cont.runs[0]
            r_cont.font.size = Pt(10)
            r_cont.font.color.rgb = RGBColor(220, 220, 220)
            
            doc.add_paragraph().space_after = Pt(12)
            
            # --- BODY ---
            # Summary
            doc.add_paragraph(data_json['profile_summary'])
            
            # Esperienza
            add_section_header(doc, "ESPERIENZA / EXPERIENCE")
            for exp in data_json['experience']:
                p_role = doc.add_paragraph()
                r_role = p_role.add_run(f"{exp['role']} | {exp['company']}")
                r_role.bold = True
                p_role.add_run(f"\n{exp['period']}").italic = True
                doc.add_paragraph(exp['description']).paragraph_format.space_after = Pt(8)
                
            # Educazione
            add_section_header(doc, "FORMAZIONE / EDUCATION")
            for edu in data_json['education']:
                doc.add_paragraph(f"{edu['degree']} - {edu['institution']} ({edu['year']})")
                
            # Skills
            add_section_header(doc, "SKILLS")
            doc.add_paragraph(", ".join(data_json['skills']))
            
            return doc

        doc_obj = create_cv_docx(data, uploaded_photo, border_width)
        bio = io.BytesIO()
        doc_obj.save(bio)
        
        st.download_button(
            "⬇️ Scarica CV in Word",
            data=bio.getvalue(),
            file_name="CV_Design.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # --- TAB LETTERA ---
    with tab_cl:
        st.subheader("Anteprima Lettera")
        st.markdown(data['cover_letter_text'])
        
        doc_cl = Document()
        for line in data['cover_letter_text'].split('\n'):
            if line.strip(): doc_cl.add_paragraph(line)
        
        bio_cl = io.BytesIO()
        doc_cl.save(bio_cl)
        
        st.download_button(
            "⬇️ Scarica Lettera in Word",
            data=bio_cl.getvalue(),
            file_name="Cover_Letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
