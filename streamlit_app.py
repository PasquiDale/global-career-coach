import streamlit as st
import google.generativeai as genai
from docx import Document
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach", page_icon="🚀", layout="wide")

# --- CSS ---
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- LOGIN ---
with st.sidebar:
    st.title("Career Coach")
    lang = st.selectbox("Lingua", ["Italiano", "English", "Deutsch", "Español", "Português"])
    st.divider()
    api_key = st.text_input("🔑 API Key (Usa quella GRATIS di AI Studio)", type="password")

    if api_key:
        try:
            genai.configure(api_key=api_key)
        except:
            pass

# --- FUNZIONE AI (USO IL MODELLO CLASSICO - MASSIMA COMPATIBILITÀ) ---
def get_ai(prompt):
    try:
        # 'gemini-pro' è il modello standard. Funziona sempre.
        model = genai.GenerativeModel('gemini-pro') 
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE: {str(e)}"

# --- TRADUZIONI ---
trans = {
    "Italiano": {"home":"🏠 Home", "cv":"📄 CV", "up":"Carica PDF", "gen":"Genera", "dl":"Scarica"},
    "English": {"home":"🏠 Home", "cv":"📄 CV", "up":"Upload PDF", "gen":"Generate", "dl":"Download"},
    "Deutsch": {"home":"🏠 Start", "cv":"📄 CV", "up":"PDF Laden", "gen":"Erstellen", "dl":"Laden"},
    "Español": {"home":"🏠 Inicio", "cv":"📄 CV", "up":"Subir PDF", "gen":"Generar", "dl":"Descargar"},
    "Português": {"home":"🏠 Início", "cv":"📄 CV", "up":"Enviar PDF", "gen":"Gerar", "dl":"Baixar"}
}
t = trans[lang]

# --- NAVIGAZIONE ---
page = st.sidebar.radio("Menu", [t["home"], t["cv"]])

if page == t["home"]:
    st.title("Global Career Coach 🚀")
    st.info("Sistema pronto. Usa la chiave gratuita di AI Studio per la massima compatibilità.")

elif page == t["cv"]:
    st.header(t["cv"])
    if not api_key:
        st.warning("⬅️ Inserisci la chiave API a sinistra.")
        st.stop()
        
    f = st.file_uploader(t["up"], type=["pdf"])
    if f and st.button(t["gen"]):
        try:
            reader = pypdf.PdfReader(f)
            txt = ""
            for p in reader.pages: txt += p.extract_text()
            
            with st.spinner("Elaborazione in corso..."):
                # Chiamo l'AI
                res = get_ai(f"Riscrivi questo CV in modo professionale in {lang}:\n{txt}")
                
                if "ERRORE" in res:
                    st.error(res)
                    st.error("Consiglio: Usa la chiave 'AI Studio' (quella che inizia con AIza). Le chiavi Cloud Enterprise spesso bloccano questo modello.")
                else:
                    doc = Document()
                    doc.add_heading('Curriculum Vitae', 0)
                    for line in res.split('\n'):
                        if line.strip(): doc.add_paragraph(line)
                    bio = io.BytesIO()
                    doc.save(bio)
                    st.success("Fatto!")
                    st.download_button(t["dl"], bio.getvalue(), "CV.docx")
        except Exception as e:
            st.error(f"Errore tecnico: {e}")
