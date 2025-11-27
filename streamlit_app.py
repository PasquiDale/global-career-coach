import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
import json
import pypdf
import re
import base64
from PIL import Image

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career AI",
    page_icon="🌍",
    layout="wide"
)

# --- 2. SISTEMA DI TRADUZIONE ---

# Mappa delle lingue disponibili
LANGUAGES = {
    "Italiano": "it",
    "English (UK)": "en_uk",
    "English (US)": "en_us",
    "Deutsch (Deutschland)": "de_de",
    "Deutsch (Schweiz)": "de_ch",
    "Español": "es",
    "Português": "pt"
}

# Dizionario dei testi dell'interfaccia
TRANSLATIONS = {
    "it": {
        "title": "AI Career Assistant",
        "sidebar_title": "Profilo & Lingua",
        "lang_label": "Seleziona Lingua / Select Language",
        "photo_label": "Foto Profilo",
        "border_label": "Spessore Bordo (px)",
        "cv_header": "1. Carica il CV",
        "cv_label": "Seleziona PDF",
        "job_header": "2. Annuncio di Lavoro",
        "job_placeholder": "Incolla qui il testo dell'offerta...",
        "btn_generate": "✨ Genera Documenti",
        "warn_cv": "⚠️ Manca il CV.",
        "warn_job": "⚠️ Manca l'Annuncio di Lavoro.",
        "success_load": "✅ CV caricato",
        "success_gen": "Analisi completata!",
        "error_json": "Errore nel formato risposta dell'AI.",
        "tab_cv": "📄 CV Revisionato",
        "tab_cl": "✉️ Lettera di Presentazione",
        "preview": "Anteprima",
        "download_cv": "⬇️ Scarica CV (.docx)",
        "download_cl": "⬇️ Scarica Lettera (.docx)",
        "processing": "Gemini 3 Pro sta scrivendo..."
    },
    "en_uk": {
        "title": "AI Career Assistant",
        "sidebar_title": "Profile & Language",
        "lang_label": "Select Language",
        "photo_label": "Profile Photo",
        "border_label": "Border Thickness (px)",
        "cv_header": "1. Upload CV",
        "cv_label": "Select PDF",
        "job_header": "2. Job Description",
        "job_placeholder": "Paste the job offer text here...",
        "btn_generate": "✨ Generate Documents",
        "warn_cv": "⚠️ CV is missing.",
        "warn_job": "⚠️ Job Description is missing.",
        "success_load": "✅ CV uploaded",
        "success_gen": "Analysis complete!",
        "error_json": "Error in AI response format.",
        "tab_cv": "📄 Revised CV",
        "tab_cl": "✉️ Cover Letter",
        "preview": "Preview",
        "download_cv": "⬇️ Download CV (.docx)",
        "download_cl": "⬇️ Download Letter (.docx)",
        "processing": "Gemini 3 Pro is writing..."
    },
    "en_us": {
        "title": "AI Career Assistant",
        "sidebar_title": "Profile & Language",
        "lang_label": "Select Language",
        "photo_label": "Profile Photo",
        "border_label": "Border Thickness (px)",
        "cv_header": "1. Upload Resume",
        "cv_label": "Select PDF",
        "job_header": "2. Job Description",
        "job_placeholder": "Paste the job offer text here...",
        "btn_generate": "✨ Generate Documents",
        "warn_cv": "⚠️ Resume is missing.",
        "warn_job": "⚠️ Job Description is missing.",
        "success_load": "✅ Resume uploaded",
        "success_gen": "Analysis complete!",
        "error_json": "Error in AI response format.",
        "tab_cv": "📄 Revised Resume",
        "tab_cl": "✉️ Cover Letter",
        "preview": "Preview",
        "download_cv": "⬇️ Download Resume (.docx)",
        "download_cl": "⬇️ Download Letter (.docx)",
        "processing": "Gemini 3 Pro is writing..."
    },
    "de_de": {
        "title": "KI Karriere-Assistent",
        "sidebar_title": "Profil & Sprache",
        "lang_label": "Sprache auswählen",
        "photo_label": "Profilbild",
        "border_label": "Rahmenbreite (px)",
        "cv_header": "1. Lebenslauf hochladen",
        "cv_label": "PDF auswählen",
        "job_header": "2. Stellenanzeige",
        "job_placeholder": "Fügen Sie hier den Text der Stellenanzeige ein...",
        "btn_generate": "✨ Dokumente generieren",
        "warn_cv": "⚠️ Lebenslauf fehlt.",
        "warn_job": "⚠️ Stellenanzeige fehlt.",
        "success_load": "✅ Lebenslauf hochgeladen",
        "success_gen": "Analyse abgeschlossen!",
        "error_json": "Fehler im KI-Antwortformat.",
        "tab_cv": "📄 Überarbeiteter Lebenslauf",
        "tab_cl": "✉️ Anschreiben",
        "preview": "Vorschau",
        "download_cv": "⬇️ Lebenslauf herunterladen (.docx)",
        "download_cl": "⬇️ Anschreiben herunterladen (.docx)",
        "processing": "Gemini 3 Pro schreibt..."
    },
    "de_ch": {
        "title": "KI Karriere-Assistent (CH)",
        "sidebar_title": "Profil & Sprache",
        "lang_label": "Sprache auswählen",
        "photo_label": "Profilbild",
        "border_label": "Rahmenbreite (px)",
        "cv_header": "1. Lebenslauf hochladen",
        "cv_label": "PDF auswählen",
        "job_header": "2. Stellenbeschrieb",
        "job_placeholder": "Fügen Sie hier den Text des Stellenbeschriebs ein...",
        "btn_generate": "✨ Dokumente generieren",
        "warn_cv": "⚠️ Lebenslauf fehlt.",
        "warn_job": "⚠️ Stellenbeschrieb fehlt.",
        "success_load": "✅ Lebenslauf hochgeladen",
        "success_gen": "Analyse abgeschlossen!",
        "error_json": "Fehler im KI-Antwortformat.",
        "tab_cv": "📄 Überarbeiteter Lebenslauf",
        "tab_cl": "✉️ Begleitschreiben",
        "preview": "Vorschau",
        "download_cv": "⬇️ Lebenslauf herunterladen (.docx)",
        "download_cl": "⬇️ Begleitschreiben herunterladen (.docx)",
        "processing": "Gemini 3 Pro schreibt..."
    },
    "es": {
        "title": "Asistente de Carrera IA",
        "sidebar_title": "Perfil e Idioma",
        "lang_label": "Seleccionar Idioma",
        "photo_label": "Foto de Perfil",
        "border_label": "Grosor del borde (px)",
        "cv_header": "1. Subir CV",
        "cv_label": "Seleccionar PDF",
        "job_header": "2. Oferta de Trabajo",
        "job_placeholder": "Pega aquí el texto de la oferta...",
        "btn_generate": "✨ Generar Documentos",
        "warn_cv": "⚠️ Falta el CV.",
        "warn_job": "⚠️ Falta la oferta de trabajo.",
        "success_load": "✅ CV cargado",
        "success_gen": "¡Análisis completado!",
        "error_json": "Error en el formato de respuesta de la IA.",
        "tab_cv": "📄 CV Revisado",
        "tab_cl": "✉️ Carta de Presentación",
        "preview": "Vista previa",
        "download_cv": "⬇️ Descargar CV (.docx)",
        "download_cl": "⬇️ Descargar Carta (.docx)",
        "processing": "Gemini 3 Pro escribiendo..."
    },
    "pt": {
        "title": "Assistente de Carreira IA",
        "sidebar_title": "Perfil e Idioma",
        "lang_label": "Selecionar Idioma",
        "photo_label": "Foto de Perfil",
        "border_label": "Espessura da borda (px)",
        "cv_header": "1. Carregar CV",
        "cv_label": "Selecionar PDF",
        "job_header": "2. Anúncio de Emprego",
        "job_placeholder": "Cole aqui o texto da vaga...",
        "btn_generate": "✨ Gerar Documentos",
        "warn_cv": "⚠️ Falta o CV.",
        "warn_job": "⚠️ Falta o anúncio de emprego.",
        "success_load": "✅ CV carregado",
        "success_gen": "Análise concluída!",
        "error_json": "Erro no formato de resposta da IA.",
        "tab_cv": "📄 CV Revisado",
        "tab_cl": "✉️ Carta de Apresentação",
        "preview": "Pré-visualização",
        "download_cv": "⬇️ Baixar CV (.docx)",
        "download_cl": "⬇️ Baixar Carta (.docx)",
        "processing": "Gemini 3 Pro escrevendo..."
    }
}

# --- 3. GESTIONE STATO ---
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "cv_text_extracted" not in st.session_state:
    st.session_state.cv_text_extracted = ""
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None

# --- 4. CONFIGURAZIONE API ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 CRITICAL ERROR: GEMINI_API_KEY missing in secrets.")
    st.stop()

# --- 5. FUNZIONI LOGICHE ---

def get_language_prompt(lang_code):
    """
    Restituisce l'istruzione specifica per la lingua richiesta.
    """
    prompts = {
        "it": "Write exclusively in Italian.",
        "en_uk": "Write in British English (UK spelling).",
        "en_us": "Write in American English (US spelling).",
        "de_de": "Write in Standard German (Germany).",
        "de_ch": "Write in Swiss Standard German. IMPORTANT: DO NOT use the character 'ß', replace it with 'ss' everywhere.",
        "es": "Write in Spanish.",
        "pt": "Write in Portuguese."
    }
    return prompts.get(lang_code, "Write in English.")

def get_gemini_response(cv_text, job_desc, lang_code):
    try:
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        lang_instruction = get_language_prompt(lang_code)
        
        prompt = f"""
        You are a Senior HR and Career Coach expert.
        
        LANGUAGE INSTRUCTION: {lang_instruction}
        
        [CANDIDATE CV]:
        {cv_text}
        
        [JOB DESCRIPTION]:
        {job_desc}
        
        [TASK]:
        1. Rewrite the CV to be more professional and tailored to the job description (in the target language).
        2. Write a persuasive Cover Letter tailored to the job description (in the target language).
        
        [REQUIRED OUTPUT FORMAT]:
        Return ONLY a valid JSON object with this exact structure:
        {{
            "cv_revisionato": "...full text of the rewritten cv...",
            "lettera_presentazione": "...full text of the cover letter..."
        }}
        Do not use markdown formatting inside the JSON values.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

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

def clean_markdown_for_word(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#+\s', '', text)
    return text.strip()

def create_docx(text_content):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    cleaned_text = clean_markdown_for_word(text_content)
    
    for line in cleaned_text.split('\n'):
        line = line.strip()
        if line:
            doc.add_paragraph(line)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode()
    return None

# --- 6. INTERFACCIA GRAFICA (SIDEBAR) ---

with st.sidebar:
    # SELETTORE LINGUA (Prima azione)
    selected_lang_name = st.selectbox(
        "Language / Lingua", 
        list(LANGUAGES.keys())
    )
    lang_code = LANGUAGES[selected_lang_name]
    texts = TRANSLATIONS[lang_code] # Carica i testi nella lingua scelta
    
    st.divider()
    
    st.title(texts["sidebar_title"])
    
    # FOTO e SLIDER
    st.subheader(texts["photo_label"])
    uploaded_photo = st.file_uploader(texts["photo_label"], type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
    
    border_width = st.slider(texts["border_label"], 0, 20, 5)
    
    if uploaded_photo:
        img_b64 = image_to_base64(uploaded_photo)
        if img_b64:
            st.markdown(
                f"""
                <style>
                .profile-img {{
                    width: 150px;
                    height: 150px;
                    object-fit: cover;
                    border-radius: 50%;
                    border: {border_width}px solid #4F8BF9;
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                }}
                </style>
                <img src="data:image/png;base64,{img_b64}" class="profile-img">
                """,
                unsafe_allow_html=True
            )

# --- 7. INTERFACCIA GRAFICA (MAIN) ---

st.title(texts["title"])
st.caption("Powered by **Gemini 3 Pro**")

col1, col2 = st.columns(2)

with col1:
    st.subheader(texts["cv_header"])
    uploaded_cv = st.file_uploader(texts["cv_label"], type="pdf")
    if uploaded_cv:
        extracted = extract_text_from_pdf(uploaded_cv)
        if extracted:
            st.session_state.cv_text_extracted = extracted
            st.success(texts["success_load"])

with col2:
    st.subheader(texts["job_header"])
    st.text_area(
        texts["job_placeholder"],
        height=200,
        key="job_description",
        label_visibility="hidden"
    )

st.markdown("---")

# --- 8. LOGICA ESECUZIONE ---

if st.button(texts["btn_generate"], type="primary", use_container_width=True):
    if not st.session_state.cv_text_extracted:
        st.warning(texts["warn_cv"])
    elif not st.session_state.job_description:
        st.warning(texts["warn_job"])
    else:
        with st.spinner(texts["processing"]):
            
            raw_response = get_gemini_response(
                st.session_state.cv_text_extracted,
                st.session_state.job_description,
                lang_code # Passo la lingua al generatore
            )
            
            if raw_response:
                try:
                    clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    st.session_state.generated_content = data
                    st.success(texts["success_gen"])
                except json.JSONDecodeError:
                    st.error(texts["error_json"])

# --- 9. OUTPUT E DOWNLOAD ---

if st.session_state.generated_content:
    st.divider()
    
    cv_final = st.session_state.generated_content.get("cv_revisionato", "")
    cl_final = st.session_state.generated_content.get("lettera_presentazione", "")
    
    tab_cv, tab_cl = st.tabs([texts["tab_cv"], texts["tab_cl"]])
    
    with tab_cv:
        st.subheader(texts["preview"])
        st.text_area("CV", value=cv_final, height=400, label_visibility="collapsed")
        
        docx_cv = create_docx(cv_final)
        st.download_button(
            label=texts["download_cv"],
            data=docx_cv,
            file_name="CV_Optimized.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    with tab_cl:
        st.subheader(texts["preview"])
        st.text_area("Letter", value=cl_final, height=400, label_visibility="collapsed")
        
        docx_cl = create_docx(cl_final)
        st.download_button(
            label=texts["download_cl"],
            data=docx_cl,
            file_name="Cover_Letter.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
