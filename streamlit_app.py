import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
import json
import pypdf
import re
from PIL import Image

# --- 1. CONFIGURAZIONE PAGINA E STATO ---
st.set_page_config(
    page_title="AI Career Assistant",
    page_icon="🚀",
    layout="wide"
)

# Inizializzazione Session State (Fondamentale per la persistenza dei dati)
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "cv_text_extracted" not in st.session_state:
    st.session_state.cv_text_extracted = ""
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None

# --- 2. CONFIGURAZIONE API GOOGLE (GEMINI) ---
try:
    # Recupero chiave dai Secrets di Streamlit
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 Errore Critico: La chiave 'GEMINI_API_KEY' non è stata trovata nei Secrets di Streamlit.")
    st.info("Configura la chiave nelle impostazioni avanzate della tua app su Streamlit Cloud.")
    st.stop() # Blocca l'esecuzione se manca la chiave

# --- 3. FUNZIONI DI UTILITÀ ---

def extract_text_from_pdf(uploaded_file):
    """Estrae il testo grezzo dal PDF caricato."""
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
    """
    Pulisce il testo dai marcatori Markdown per un documento Word professionale.
    """
    if not text: return ""
    # Rimuove il grassetto (**testo**) lasciando il testo
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Rimuove il corsivo (*testo*)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Rimuove i titoli Markdown (## Titolo)
    text = re.sub(r'#+\s', '', text)
    return text.strip()

def create_docx(text_content):
    """Genera un file .docx in memoria partendo dal testo pulito."""
    doc = Document()
    
    # Impostazioni stile base
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    # Pulizia e inserimento
    clean_text = clean_markdown_for_word(text_content)
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if line:
            doc.add_paragraph(line)
            
    # Salvataggio nel buffer di memoria
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_with_gemini_3(cv_text, job_desc):
    """
    Chiama Gemini 3.0 Pro per elaborare i contenuti in JSON.
    """
    # CONFIGURAZIONE MODELLO RICHIESTA (Versione 3.0 Pro)
    try:
        model = genai.GenerativeModel("gemini-3.0-pro")
        
        prompt = f"""
        Sei un Career Coach esperto. Analizza il seguente CV e l'Annuncio di lavoro.
        
        [CV DEL CANDIDATO]:
        {cv_text}
        
        [ANNUNCIO DI LAVORO]:
        {job_desc}
        
        [COMPITO]:
        1. Riscrivi il CV migliorandolo, rendendolo professionale e mirato per l'annuncio.
        2. Scrivi una Lettera di Presentazione persuasiva che colleghi le esperienze del candidato ai requisiti.
        
        [FORMATO OUTPUT RICHIESTO]:
        Devi restituire SOLO un JSON valido (senza markdown ```json) con questa struttura esatta:
        {{
            "cv_text": "...testo completo del cv...",
            "cover_letter_text": "...testo completo della lettera..."
        }}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Errore durante la chiamata a Gemini 3.0 Pro: {e}")
        return None

# --- 4. INTERFACCIA UTENTE (SIDEBAR) ---

with st.sidebar:
    st.title("Impostazioni Profilo")
    
    st.subheader("La tua Foto")
    uploaded_photo = st.file_uploader("Carica foto profilo", type=['jpg', 'png', 'jpeg'])
    
    border_width = st.slider("Spessore bordo foto (px)", 0, 20, 5)
    
    # Visualizzazione foto con bordo CSS dinamico
    if uploaded_photo:
        image = Image.open(uploaded_photo)
        st.markdown(
            f"""
            <style>
            .profile-pic {{
                border: {border_width}px solid #4CAF50; /* Colore verde esempio */
                border-radius: 50%;
                display: block;
                margin-left: auto;
                margin-right: auto;
                width: 150px;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        st.image(image, caption="Anteprima Foto", width=150)
        st.info(f"Bordo applicato: {border_width}px")
    else:
        st.markdown("Nessuna foto caricata.")

# --- 5. INTERFACCIA UTENTE (MAIN PAGE) ---

st.title("🤖 AI Career Assistant")
st.markdown("Genera documenti professionali ottimizzati con **Gemini 3.0 Pro**.")

col_input1, col_input2 = st.columns(2)

with col_input1:
    st.subheader("1. Carica il CV")
    uploaded_cv = st.file_uploader("Seleziona il tuo CV (PDF)", type="pdf")
    
    if uploaded_cv:
        extracted = extract_text_from_pdf(uploaded_cv)
        if extracted:
            st.session_state.cv_text_extracted = extracted
            st.success("✅ CV letto con successo")

with col_input2:
    st.subheader("2. Annuncio di Lavoro")
    # Text area collegata a session_state per non perdere il testo al reload
    st.text_area(
        "Inserisci qui il testo dell'offerta",
        height=200,
        key="job_description", 
        placeholder="Incolla qui la Job Description..."
    )

st.markdown("---")

# --- 6. LOGICA DI GENERAZIONE ---

if st.button("✨ Genera Documenti", type="primary", use_container_width=True):
    # Controlli preliminari
    if not st.session_state.cv_text_extracted:
        st.warning("⚠️ Manca il CV. Carica un file PDF nella colonna sinistra.")
    elif not st.session_state.job_description:
        st.warning("⚠️ Manca l'Annuncio di Lavoro. Inseriscilo nella colonna destra.")
    else:
        with st.spinner("Gemini 3.0 Pro sta elaborando i tuoi documenti..."):
            
            raw_response = generate_with_gemini_3(
                st.session_state.cv_text_extracted,
                st.session_state.job_description
            )
            
            if raw_response:
                try:
                    # Pulizia stringa JSON (rimozione eventuali backticks del markdown)
                    clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    # Salvataggio nel Session State
                    st.session_state.generated_content = data
                    st.success("Elaborazione completata con successo!")
                    
                except json.JSONDecodeError:
                    st.error("Errore nella lettura della risposta AI. Il modello non ha restituito un JSON valido. Riprova.")

# --- 7. VISUALIZZAZIONE RISULTATI E DOWNLOAD ---

if st.session_state.generated_content:
    st.divider()
    st.subheader("📄 I tuoi Documenti Generati")
    
    # Recupero dati dal JSON
    cv_content = st.session_state.generated_content.get("cv_text", "")
    cl_content = st.session_state.generated_content.get("cover_letter_text", "")
    
    # Tabs per organizzare l'output
    tab1, tab2 = st.tabs(["CV Generato", "Lettera di Presentazione"])
    
    # TAB 1: CV
    with tab1:
        st.markdown("### Anteprima CV Riscritto")
        st.text_area("Contenuto CV", value=cv_content, height=400)
        
        # Generazione file Word in memoria
        docx_cv = create_docx(cv_content)
        
        st.download_button(
            label="⬇️ Scarica CV in Word (.docx)",
            data=docx_cv,
            file_name="CV_Revisionato.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_cv_btn"
        )
        
    # TAB 2: LETTERA
    with tab2:
        st.markdown("### Anteprima Lettera")
        st.text_area("Contenuto Lettera", value=cl_content, height=400)
        
        # Generazione file Word in memoria
        docx_cl = create_docx(cl_content)
        
        st.download_button(
            label="⬇️ Scarica Lettera in Word (.docx)",
            data=docx_cl,
            file_name="Lettera_Presentazione.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_cl_btn"
        )
