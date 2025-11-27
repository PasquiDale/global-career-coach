import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
import json
import pypdf
import re

# --- 1. CONFIGURAZIONE PAGINA E STATO ---
st.set_page_config(
    page_title="AI Career Assistant",
    page_icon="🚀",
    layout="wide"
)

# Inizializzazione Session State (Fondamentale per non perdere i dati al reload)
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "cv_text_extracted" not in st.session_state:
    st.session_state.cv_text_extracted = ""
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None

# --- 2. CONFIGURAZIONE API GOOGLE (GEMINI) ---
try:
    # Recupero chiave ESATTA come richiesto
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("🚨 Errore Critico: La chiave 'GEMINI_API_KEY' non è stata trovata nei Secrets di Streamlit.")
    st.stop()
except Exception as e:
    st.error(f"🚨 Errore di configurazione API: {e}")
    st.stop()

# --- 3. FUNZIONI DI UTILITÀ ---

def extract_text_from_pdf(uploaded_file):
    """Estrae il testo grezzo dal PDF."""
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
    Rimuove la sintassi Markdown per rendere il file Word pulito e professionale.
    """
    if not text: return ""
    
    # Rimuove il grassetto (**testo**) mantenendo il testo
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Rimuove il corsivo (*testo*)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Rimuove i titoli Markdown (## Titolo)
    text = re.sub(r'#+\s', '', text)
    # Rimuove bullet points markdown se necessario, o li lascia per Word
    # Qui puliamo eventuali caratteri strani residui
    return text.strip()

def create_docx(text_content):
    """Genera un file .docx in memoria partendo dal testo pulito."""
    doc = Document()
    
    # Impostazioni stile base
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    # Pulizia del testo dai simboli markdown
    clean_text = clean_markdown_for_word(text_content)
    
    # Aggiunta paragrafi
    for line in clean_text.split('\n'):
        line = line.strip()
        if line:
            doc.add_paragraph(line)
            
    # Salvataggio nel buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_with_gemini(cv_text, job_desc):
    """
    Chiama Gemini 3.0 Pro per elaborare i contenuti in JSON.
    """
    # Configurazione Modello
    model = genai.GenerativeModel("gemini-1.5-pro") 
    # NOTA: Uso "gemini-1.5-pro" perché "gemini-3.0-pro" non è ancora un nome standard pubblico stabile API.
    # Se hai accesso alla beta privata 3.0, cambia la stringa sopra in "gemini-3.0-pro-preview" o simile.
    # Per stabilità ora uso il modello Pro più recente disponibile pubblicamente.
    
    prompt = f"""
    Sei un Career Coach esperto. Analizza il seguente CV e l'Annuncio di lavoro.
    
    [CV DEL CANDIDATO]:
    {cv_text}
    
    [ANNUNCIO DI LAVORO]:
    {job_desc}
    
    [COMPITO]:
    1. Riscrivi il CV migliorandolo, rendendolo professionale e mirato per l'annuncio.
    2. Scrivi una Lettera di Presentazione persuasiva che colleghi le esperienze del candidato ai requisiti.
    
    [FORMATO OUTPUT]:
    Devi restituire SOLO un JSON valido (senza markdown ```json) con questa struttura esatta:
    {{
        "cv_content": "...testo completo del cv...",
        "cover_letter_content": "...testo completo della lettera..."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Errore durante la generazione con Gemini: {e}")
        return None

# --- 4. INTERFACCIA UTENTE (UI) ---

st.title("🤖 AI Career Assistant")
st.markdown("Carica il tuo CV e l'annuncio per generare documenti professionali in Word.")

# Layout a due colonne per gli input
col_input1, col_input2 = st.columns(2)

with col_input1:
    st.subheader("1. Carica il CV")
    uploaded_file = st.file_uploader("Seleziona il tuo CV (PDF)", type="pdf")
    if uploaded_file:
        extracted = extract_text_from_pdf(uploaded_file)
        if extracted:
            st.session_state.cv_text_extracted = extracted
            st.success("✅ CV letto con successo")

with col_input2:
    st.subheader("2. Annuncio di Lavoro")
    # Text area collegata a session_state per non perdere il testo
    st.text_area(
        "Inserisci qui il testo dell'offerta",
        height=200,
        key="job_description", # Questo collega automaticamente il widget a st.session_state.job_description
        placeholder="Incolla qui la Job Description..."
    )

st.markdown("---")

# Bottone di Generazione
if st.button("✨ Genera Documenti", type="primary", use_container_width=True):
    if not st.session_state.cv_text_extracted:
        st.warning("⚠️ Manca il CV. Carica un file PDF.")
    elif not st.session_state.job_description:
        st.warning("⚠️ Manca l'Annuncio di Lavoro.")
    else:
        with st.spinner("Gemini sta elaborando il tuo profilo..."):
            raw_response = generate_with_gemini(
                st.session_state.cv_text_extracted,
                st.session_state.job_description
            )
            
            if raw_response:
                try:
                    # Pulizia stringa JSON (rimozione eventuali backticks)
                    clean_json = raw_response.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    st.session_state.generated_content = data
                    st.success("Elaborazione completata!")
                except json.JSONDecodeError:
                    st.error("Errore nella lettura della risposta AI. Riprova.")

# --- 5. OUTPUT VISIVO E DOWNLOAD ---

if st.session_state.generated_content:
    st.divider()
    st.subheader("📄 I tuoi Documenti")
    
    cv_content = st.session_state.generated_content.get("cv_content", "")
    cl_content = st.session_state.generated_content.get("cover_letter_content", "")
    
    tab1, tab2 = st.tabs(["CV Revisionato", "Lettera di Presentazione"])
    
    # TAB 1: CV
    with tab1:
        st.markdown("### Anteprima CV")
        st.markdown(cv_content) # Mostra anteprima con formattazione
        
        # Genera Word
        docx_cv = create_docx(cv_content)
        st.download_button(
            label="⬇️ Scarica CV in Word (.docx)",
            data=docx_cv,
            file_name="CV_Revisionato.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    # TAB 2: LETTERA
    with tab2:
        st.markdown("### Anteprima Lettera")
        st.markdown(cl_content) # Mostra anteprima con formattazione
        
        # Genera Word
        docx_cl = create_docx(cl_content)
        st.download_button(
            label="⬇️ Scarica Lettera in Word (.docx)",
            data=docx_cl,
            file_name="Lettera_Presentazione.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
