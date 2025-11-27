import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
import json
import pypdf
import re
from PIL import Image, ImageOps

# --- 1. CONFIGURAZIONE PAGINA E STATO ---
st.set_page_config(
    page_title="AI Career Assistant Pro",
    page_icon="🚀",
    layout="wide"
)

# Inizializzazione Session State per persistenza dati
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "cv_text_extracted" not in st.session_state:
    st.session_state.cv_text_extracted = ""
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None
if "current_model_used" not in st.session_state:
    st.session_state.current_model_used = ""

# --- 2. CONFIGURAZIONE API KEY ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 ERRORE CRITICO: Chiave API mancante.")
    st.warning("Assicurati di aver impostato `GEMINI_API_KEY` nei Secrets di Streamlit Cloud.")
    st.stop()

# --- 3. FUNZIONI UTILITY (Backend) ---

def extract_text_from_pdf(uploaded_file):
    """Estrae testo grezzo dal PDF."""
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
        return None

def clean_markdown(text):
    """Pulisce il testo da formattazione Markdown per Word."""
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # Via grassetto
    text = re.sub(r'\*(.*?)\*', r'\1', text)     # Via corsivo
    text = re.sub(r'#+\s', '', text)             # Via titoli
    return text.strip()

def create_docx(text_content):
    """Crea un file .docx in memoria."""
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    cleaned = clean_markdown(text_content)
    
    for line in cleaned.split('\n'):
        line = line.strip()
        if line:
            doc.add_paragraph(line)
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_with_fallback(cv_text, job_desc):
    """
    Logica CORE: Tenta Gemini 3.0 Pro, se fallisce passa a 1.5 Pro.
    Restituisce il JSON generato e il nome del modello usato.
    """
    
    prompt = f"""
    Sei un Senior HR Specialist.
    
    [CV CANDIDATO]:
    {cv_text[:30000]} 
    
    [ANNUNCIO DI LAVORO]:
    {job_desc}
    
    [COMPITO]:
    1. Riscrivi il CV ottimizzandolo per l'annuncio.
    2. Scrivi una Lettera di Presentazione persuasiva.
    
    [OUTPUT OBBLIGATORIO]:
    Rispondi SOLO con un JSON valido con queste chiavi:
    {{
        "cv_text": "...testo del cv...",
        "cover_letter_text": "...testo della lettera..."
    }}
    Non aggiungere markdown (```json).
    """

    # --- TENTATIVO 1: GEMINI 3.0 PRO ---
    try:
        model = genai.GenerativeModel("gemini-3.0-pro")
        response = model.generate_content(prompt)
        return response.text, "Gemini 3.0 Pro"
    except Exception as e_30:
        # --- TENTATIVO 2 (FALLBACK): GEMINI 1.5 PRO ---
        # Se siamo qui, il 3.0 ha fallito (404 o altro). Non fermiamo l'app.
        print(f"Fallback triggered: {e_30}") # Log interno
        try:
            model_fallback = genai.GenerativeModel("gemini-1.5-pro")
            response = model_fallback.generate_content(prompt)
            return response.text, "Gemini 1.5 Pro (Fallback)"
        except Exception as e_15:
            st.error(f"Errore fatale su entrambi i modelli: {e_15}")
            return None, None

# --- 4. INTERFACCIA: SIDEBAR (FOTO) ---
with st.sidebar:
    st.title("📸 Impostazioni Profilo")
    st.info("Carica la tua foto per visualizzare l'anteprima con bordo.")
    
    uploaded_photo = st.file_uploader("Carica Foto (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
    border_width = st.slider("Spessore bordo (px)", 0, 20, 5)
    
    if uploaded_photo:
        try:
            image = Image.open(uploaded_photo)
            # Aggiungiamo bordo usando PIL per un'anteprima reale
            # Convertiamo in RGB se necessario
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            img_with_border = ImageOps.expand(image, border=border_width, fill='white') # Bordo bianco o colorato
            
            st.image(img_with_border, caption="Anteprima Foto", use_column_width=True)
            
            # CSS Hack per mostrare visivamente il bordo colorato nell'app se lo sfondo è bianco
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center;">
                    <div style="border: {border_width}px solid #4F8BF9; border-radius: 8px; padding: 5px; display: inline-block;">
                        <span style="font-size: 12px; color: gray;">Simulazione Bordo Blu</span>
                    </div>
                </div>
                """, unsafe_allow_html=True
            )
        except Exception as e:
            st.error("Errore caricamento immagine")

# --- 5. INTERFACCIA: MAIN PAGE ---
st.title("🤖 AI Career Assistant")
st.markdown("Genera CV e Lettera ottimizzati. Il sistema usa **Gemini 3.0** (con fallback automatico).")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Carica CV")
    uploaded_cv = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_cv:
        extracted = extract_text_from_pdf(uploaded_cv)
        if extracted:
            st.session_state.cv_text_extracted = extracted
            st.success("✅ CV Letto")

with col2:
    st.subheader("2. Annuncio di Lavoro")
    # Colleghiamo direttamente al session_state tramite key
    st.text_area(
        "Incolla qui la Job Description",
        height=200,
        key="job_description",
        placeholder="Incolla qui il testo dell'offerta..."
    )

st.markdown("---")

# --- 6. LOGICA DI ESECUZIONE ---
if st.button("✨ Genera Documenti", type="primary", use_container_width=True):
    if not st.session_state.cv_text_extracted:
        st.warning("⚠️ Manca il CV.")
    elif not st.session_state.job_description:
        st.warning("⚠️ Manca l'Annuncio di Lavoro.")
    else:
        with st.spinner("Analisi in corso... (Tentativo con Gemini 3.0 Pro)"):
            
            raw_text, model_name = generate_with_fallback(
                st.session_state.cv_text_extracted,
                st.session_state.job_description
            )
            
            if raw_text:
                try:
                    # Pulizia JSON
                    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    st.session_state.generated_content = data
                    st.session_state.current_model_used = model_name
                    st.success(f"Fatto! Generato usando: **{model_name}**")
                    
                except json.JSONDecodeError:
                    st.error("Errore nel formato della risposta AI. Riprova.")

# --- 7. OUTPUT E DOWNLOAD ---
if st.session_state.generated_content:
    st.divider()
    
    cv_out = st.session_state.generated_content.get("cv_text", "")
    cl_out = st.session_state.generated_content.get("cover_letter_text", "")
    
    tab1, tab2 = st.tabs(["📄 CV Generato", "✉️ Lettera di Presentazione"])
    
    with tab1:
        st.subheader("Anteprima CV")
        st.text_area("Testo CV", value=cv_out, height=400)
        
        docx_cv = create_docx(cv_out)
        st.download_button(
            label="⬇️ Scarica CV (.docx)",
            data=docx_cv,
            file_name="CV_Ottimizzato.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    with tab2:
        st.subheader("Anteprima Lettera")
        st.text_area("Testo Lettera", value=cl_out, height=400)
        
        docx_cl = create_docx(cl_out)
        st.download_button(
            label="⬇️ Scarica Lettera (.docx)",
            data=docx_cl,
            file_name="Lettera_Presentazione.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
