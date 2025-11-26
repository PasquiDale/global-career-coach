import streamlit as st
import google.generativeai as genai
from docx import Document
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach", layout="wide")

# --- GESTIONE CHIAVE ---
# Proviamo a recuperarla dai secrets, se no la chiediamo a mano
api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.title("Configurazione")
    # Se la chiave non c'è nei secrets, mostriamo il campo
    if not api_key:
        api_key = st.text_input("Inserisci API Key", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Errore Key: {e}")

# --- FUNZIONE UNIVERSALE (GEMINI PRO CLASSICO) ---
def get_gemini_response(prompt):
    try:
        # USIAMO IL MODELLO CLASSICO, QUELLO CHE NON FALLISCE MAI
        # Se questo non va, nulla andrà.
        model = genai.GenerativeModel('gemini-pro') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERRORE: {str(e)}"

# --- TRADUZIONI ---
translations = {
    "Italiano": {"title": "Riformatta CV", "up": "Carica PDF", "btn": "Genera", "dl": "Scarica Word"},
    "English": {"title": "Reformat CV", "up": "Upload PDF", "btn": "Generate", "dl": "Download Word"},
    "Deutsch": {"title": "Lebenslauf", "up": "PDF hochladen", "btn": "Erstellen", "dl": "Word laden"},
    "Español": {"title": "Reformatear CV", "up": "Subir PDF", "btn": "Generar", "dl": "Descargar Word"},
    "Português": {"title": "Reformatar CV", "up": "Enviar PDF", "btn": "Gerar", "dl": "Baixar Word"}
}

# --- INTERFACCIA ---
lang = st.sidebar.selectbox("Lingua", ["Italiano", "English", "Deutsch", "Español", "Português"])
t = translations[lang]

st.title("Global Career Coach 🚀")

# SEZIONE CV (Semplificata per testare)
st.header(t["title"])

if not api_key:
    st.warning("Inserisci la chiave API nella barra laterale per iniziare.")
    st.stop()

uploaded_file = st.file_uploader(t["up"], type=["pdf"])

if uploaded_file and st.button(t["btn"]):
    # Lettura PDF
    try:
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    except:
        st.error("Errore nella lettura del PDF.")
        st.stop()

    with st.spinner("L'AI sta scrivendo... (Modello Standard)"):
        # Chiamata AI
        response_text = get_gemini_response(f"Riscrivi questo CV in modo professionale in {lang}:\n{text}")
        
        if "ERRORE" in response_text:
            st.error(response_text)
            st.info("Se vedi 404, la tua chiave non ha accesso nemmeno al modello base.")
        else:
            # Creazione Word
            doc = Document()
            doc.add_heading('Curriculum Vitae', 0)
            for line in response_text.split('\n'):
                if line.strip():
                    doc.add_paragraph(line)
            
            bio = io.BytesIO()
            doc.save(bio)
            
            st.success("Fatto!")
            st.download_button(
                label=t["dl"],
                data=bio.getvalue(),
                file_name="CV_Optimized.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
