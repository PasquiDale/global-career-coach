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

# --- 1. CONFIGURAZIONE PAGINA E STATO ---
st.set_page_config(
    page_title="AI Career Assistant Pro",
    page_icon="🚀",
    layout="wide"
)

# Inizializzazione Session State (Fondamentale per persistenza dati)
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "cv_text_extracted" not in st.session_state:
    st.session_state.cv_text_extracted = ""
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None

# --- 2. CONFIGURAZIONE API KEY E MODELLO ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 ERRORE CRITICO: Chiave API mancante nei Secrets.")
    st.stop()

def get_gemini_response(cv_text, job_desc):
    """
    Chiama il modello specifico models/gemini-3-pro-preview.
    """
    try:
        # CONFIGURAZIONE ESATTA RICHIESTA
        model = genai.GenerativeModel("models/gemini-3-pro-preview")
        
        prompt = f"""
        Sei un Senior HR e Career Coach. Analizza i seguenti documenti.
        
        [CV CANDIDATO]:
        {cv_text}
        
        [ANNUNCIO DI LAVORO]:
        {job_desc}
        
        [COMPITO]:
        1. Riscrivi il CV rendendolo più professionale e allineato all'annuncio.
        2. Scrivi una Lettera di Presentazione persuasiva e mirata.
        
        [FORMATO OUTPUT OBBLIGATORIO]:
        Restituisci SOLAMENTE un JSON valido con questa struttura esatta:
        {{
            "cv_revisionato": "...testo del cv...",
            "lettera_presentazione": "...testo della lettera..."
        }}
        Non usare markdown nel JSON.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Errore API Gemini: {e}")
        return None

# --- 3. FUNZIONI UTILITY (PDF, WORD, IMMAGINI) ---

def extract_text_from_pdf(uploaded_file):
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
        return None

def clean_markdown_for_word(text):
    """Pulisce il testo dai simboli Markdown."""
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # Via grassetto
    text = re.sub(r'\*(.*?)\*', r'\1', text)     # Via corsivo
    text = re.sub(r'#+\s', '', text)             # Via titoli
    return text.strip()

def create_docx(text_content):
    """Crea un file .docx pulito in memoria."""
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
    """Converte l'immagine caricata in base64 per l'HTML."""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode()
    return None

# --- 4. SIDEBAR: IMPOSTAZIONI PROFILO ---
with st.sidebar:
    st.title("👤 Il tuo Profilo")
    
    st.subheader("Foto Profilo")
    uploaded_photo = st.file_uploader("Carica la tua foto", type=['jpg', 'png', 'jpeg'])
    
    border_width = st.slider("Spessore Bordo Foto (px)", 0, 20, 5)
    
    if uploaded_photo:
        # Anteprima con CSS personalizzato
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
                <p style="text-align:center; margin-top:10px;">Anteprima Foto</p>
                """,
                unsafe_allow_html=True
            )

# --- 5. MAIN PAGE: INPUT DATI ---
st.title("🚀 AI Career Assistant")
st.caption("Powered by **Gemini 3 Pro**")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Carica il CV")
    uploaded_cv = st.file_uploader("Seleziona PDF", type="pdf")
    if uploaded_cv:
        extracted = extract_text_from_pdf(uploaded_cv)
        if extracted:
            st.session_state.cv_text_extracted = extracted
            st.success("✅ CV caricato")

with col2:
    st.subheader("2. Annuncio di Lavoro")
    # Colleghiamo la text area direttamente al session state tramite 'key'
    # Questo assicura che il testo non sparisca mai
    st.text_area(
        "Incolla qui la Job Description",
        height=200,
        key="job_description",
        placeholder="Incolla qui il testo dell'offerta..."
    )

st.markdown("---")

# --- 6. LOGICA DI GENERAZIONE ---
if st.button("✨ Genera Documenti", type="primary", use_container_width=True):
    # Validazione
    if not st.session_state.cv_text_extracted:
        st.warning("⚠️ Manca il CV.")
    elif not st.session_state.job_description:
        st.warning("⚠️ Manca l'Annuncio di Lavoro.")
    else:
        with st.spinner("Gemini 3 Pro sta analizzando il tuo profilo..."):
            
            # Chiamata al modello specifico
            raw_response = get_gemini_response(
                st.session_state.cv_text_extracted,
                st.session_state.job_description
            )
            
            if raw_response:
                try:
                    # Pulizia JSON (rimozione markdown backticks se presenti)
                    clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    st.session_state.generated_content = data
                    st.success("Analisi completata!")
                    
                except json.JSONDecodeError:
                    st.error("Errore nel formato risposta dell'AI. Riprova.")

# --- 7. OUTPUT E DOWNLOAD ---
if st.session_state.generated_content:
    st.divider()
    
    cv_final = st.session_state.generated_content.get("cv_revisionato", "")
    cl_final = st.session_state.generated_content.get("lettera_presentazione", "")
    
    tab_cv, tab_cl = st.tabs(["📄 CV Revisionato", "✉️ Lettera di Presentazione"])
    
    # TAB 1: CV
    with tab_cv:
        st.subheader("Anteprima CV")
        st.text_area("Contenuto", value=cv_final, height=400, label_visibility="collapsed")
        
        docx_cv = create_docx(cv_final)
        st.download_button(
            label="⬇️ Scarica CV in Word (.docx)",
            data=docx_cv,
            file_name="CV_Revisionato.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    # TAB 2: Lettera
    with tab_cl:
        st.subheader("Anteprima Lettera")
        st.text_area("Contenuto", value=cl_final, height=400, label_visibility="collapsed")
        
        docx_cl = create_docx(cl_final)
        st.download_button(
            label="⬇️ Scarica Lettera in Word (.docx)",
            data=docx_cl,
            file_name="Lettera_Presentazione.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
