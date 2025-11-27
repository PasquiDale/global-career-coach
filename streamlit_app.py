import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
import json
import pypdf
import re

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Career AI Assistant",
    page_icon="🚀",
    layout="wide"
)

# --- GESTIONE STATO (SESSION STATE) ---
# Fondamentale per non perdere i dati durante i re-run di Streamlit
if "cv_text_original" not in st.session_state:
    st.session_state.cv_text_original = ""
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "generated_cv" not in st.session_state:
    st.session_state.generated_cv = None
if "generated_letter" not in st.session_state:
    st.session_state.generated_letter = None

# --- GESTIONE API KEY (DA SECRETS) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 Errore Critico: Chiave API mancante nei Secrets.")
    st.info("Configura 'GOOGLE_API_KEY' nelle impostazioni avanzate di Streamlit Cloud.")
    st.stop() # Ferma l'esecuzione se manca la chiave

# --- FUNZIONI DI UTILITÀ ---

def extract_text_from_pdf(uploaded_file):
    """Estrae testo puro da un file PDF caricato."""
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Errore nella lettura del PDF: {e}")
        return None

def clean_markdown_for_word(text):
    """
    Pulisce il testo dai marcatori Markdown (**, ##, etc) per renderlo
    adatto a un documento Word formale.
    """
    if not text: return ""
    # Rimuove bold (**)
    text = text.replace("**", "")
    # Rimuove intestazioni markdown (## )
    text = text.replace("## ", "").replace("# ", "")
    return text

def create_docx(text_content):
    """
    Crea un oggetto BytesIO contenente il file .docx formattato.
    """
    doc = Document()
    
    # Stile di base
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Pulizia del testo e inserimento nel documento
    clean_text = clean_markdown_for_word(text_content)
    
    # Aggiunge i paragrafi gestendo le nuove righe
    for line in clean_text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)

    # Salvataggio in memoria buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_ai_content(cv_text, job_desc):
    """
    Chiama Gemini 3.0 Pro per generare CV e Lettera in formato JSON.
    """
    model = genai.GenerativeModel("gemini-1.5-pro") # Nota: Usiamo 1.5 Pro se 3.0 non è ancora in whitelist pubblica, altrimenti sostituire con "gemini-3.0-pro"
    
    prompt = f"""
    Sei un esperto selezionatore del personale e career coach.
    
    INPUT:
    1. TESTO CV ORIGINALE:
    {cv_text}
    
    2. ANNUNCIO DI LAVORO (JOB DESCRIPTION):
    {job_desc}
    
    COMPITO:
    Devi generare due testi distinti in base all'annuncio fornito:
    1. Una revisione del CV che evidenzi le esperienze pertinenti per questo lavoro specifico.
    2. Una lettera di presentazione altamente persuasiva e personalizzata.
    
    FORMATO OUTPUT RICHIESTO (JSON):
    Rispondi SOLAMENTE con un oggetto JSON valido contenente esattamente queste due chiavi:
    {{
        "cv_revisionato": "Testo completo del CV revisionato...",
        "lettera_presentazione": "Testo completo della lettera..."
    }}
    Non aggiungere markdown (```json) all'inizio o alla fine. Solo il JSON puro.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Errore durante la generazione AI: {e}")
        return None

# --- INTERFACCIA UTENTE ---

st.title("📄 Career AI: CV & Cover Letter Generator")
st.markdown("Carica il tuo CV e l'annuncio per ottenere documenti ottimizzati pronti per l'invio.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Il tuo CV")
    uploaded_file = st.file_uploader("Carica il tuo CV (PDF)", type="pdf")
    
    if uploaded_file is not None:
        extracted_text = extract_text_from_pdf(uploaded_file)
        if extracted_text:
            st.session_state.cv_text_original = extracted_text
            st.success("✅ CV caricato e letto correttamente.")

with col2:
    st.subheader("2. L'Annuncio")
    # Colleghiamo la text_area al session_state per non perdere il testo
    job_input = st.text_area(
        "Incolla qui il testo dell'Offerta di Lavoro", 
        height=200,
        placeholder="Copia qui la Job Description...",
        key="job_input_area" 
    )
    # Aggiorniamo lo stato manuale se necessario, ma usando key='...' lo fa streamlit in automatico
    if job_input:
        st.session_state.job_description = job_input

# --- BOTTONE DI AZIONE ---
st.markdown("---")
generate_btn = st.button("✨ Genera Documenti Ottimizzati", type="primary", use_container_width=True)

if generate_btn:
    if not st.session_state.cv_text_original:
        st.warning("⚠️ Per favore carica prima il tuo CV.")
    elif not st.session_state.job_description:
        st.warning("⚠️ Per favore incolla l'annuncio di lavoro.")
    else:
        with st.spinner("L'AI sta analizzando il profilo e scrivendo i documenti..."):
            json_response_text = generate_ai_content(
                st.session_state.cv_text_original, 
                st.session_state.job_description
            )
            
            if json_response_text:
                try:
                    # Pulizia nel caso il modello inserisca backticks
                    clean_json = json_response_text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    st.session_state.generated_cv = data.get("cv_revisionato", "")
                    st.session_state.generated_letter = data.get("lettera_presentazione", "")
                    st.success("Analisi completata!")
                    
                except json.JSONDecodeError:
                    st.error("Errore nel parsing della risposta AI. Riprova.")

# --- RISULTATI E DOWNLOAD ---
if st.session_state.generated_cv and st.session_state.generated_letter:
    
    tab_cv, tab_lettera = st.tabs(["📄 CV Ottimizzato", "✉️ Lettera di Presentazione"])
    
    with tab_cv:
        st.subheader("Anteprima CV")
        st.markdown(st.session_state.generated_cv) # Markdown per anteprima visiva
        
        # Creazione file Word
        docx_cv = create_docx(st.session_state.generated_cv)
        
        st.download_button(
            label="⬇️ Scarica CV in Word (.docx)",
            data=docx_cv,
            file_name="CV_Ottimizzato.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_cv"
        )
        
    with tab_lettera:
        st.subheader("Anteprima Lettera")
        st.markdown(st.session_state.generated_letter) # Markdown per anteprima visiva
        
        # Creazione file Word
        docx_letter = create_docx(st.session_state.generated_letter)
        
        st.download_button(
            label="⬇️ Scarica Lettera in Word (.docx)",
            data=docx_letter,
            file_name="Lettera_Presentazione.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_letter"
        )
