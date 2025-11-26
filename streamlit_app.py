import streamlit as st
import google.generativeai as genai
from docx import Document
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach", page_icon="🚀")

# --- CSS ---
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- SIDEBAR & LOGIN ---
with st.sidebar:
    st.title("🚀 Career Coach")
    lang = st.selectbox("Lingua", ["Italiano", "English", "Deutsch", "Español", "Português"])
    st.divider()
    st.markdown("### 🔑 Login")
    # Chiediamo la chiave qui per evitare problemi con i Secrets bloccati
    api_key = st.text_input("Incolla API Key (AI Studio)", type="password")

# --- CONFIGURAZIONE AI ---
if api_key:
    try:
        genai.configure(api_key=api_key)
    except:
        st.error("Formato chiave non valido.")

def get_ai(prompt):
    if not api_key: return "ERRORE: Manca la chiave."
    try:
        # Usiamo FLASH: è il più compatibile con le chiavi AI Studio
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE TECNICO: {str(e)}"

# --- INTERFACCIA ---
st.title("Assistente Carriera AI")

t_up = "Carica CV (PDF)"
t_gen = "Genera CV Word"

uploaded_file = st.file_uploader(t_up, type=["pdf"])

if uploaded_file and st.button(t_gen):
    if not api_key:
        st.warning("⚠️ Incolla la Chiave API nel menu a sinistra prima di cliccare!")
        st.stop()
        
    try:
        # 1. Leggi PDF
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for p in reader.pages: text += p.extract_text()
        
        # 2. Chiama AI
        with st.spinner("L'AI sta lavorando..."):
            prompt_text = f"Sei un esperto HR. Riscrivi questo CV in {lang} in modo professionale e action-oriented:\n{text}"
            res = get_ai(prompt_text)
            
            if "ERRORE" in res:
                st.error(res)
                st.info("💡 Suggerimento: Usa una chiave GRATUITA presa da aistudio.google.com. Le chiavi Cloud Enterprise non funzionano con questo codice.")
            else:
                # 3. Crea Word
                doc = Document()
                doc.add_heading('Curriculum Vitae', 0)
                for line in res.split('\n'):
                    if line.strip(): doc.add_paragraph(line)
                bio = io.BytesIO()
                doc.save(bio)
                
                st.success("Fatto!")
                st.download_button("Scarica CV.docx", bio.getvalue(), "CV_Pro.docx")
                
    except Exception as e:
        st.error(f"Errore imprevisto: {e}")
