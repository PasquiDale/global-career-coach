import streamlit as st
import google.generativeai as genai
from docx import Document
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Global Career Coach", page_icon="🚀", layout="wide")

# --- CSS ---
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- INTERFACCIA LINGUA ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2038/2038022.png", width=50)
    st.title("Career Coach")
    lang = st.selectbox("Lingua / Language", ["Italiano", "English", "Deutsch", "Espagnol", "Português"])
    
    st.divider()
    
    # --- INSERIMENTO CHIAVE MANUALE (Per bypassare errori) ---
    st.markdown("### 🔑 Login")
    api_key = st.text_input("Incolla qui la tua API Key (AI Studio)", type="password", help="La chiave che inizia con AIza...")
    
    if not api_key:
        st.warning("⬅️ Incolla la chiave qui sopra per iniziare.")
        st.stop() # Blocca tutto se non c'è la chiave

    # Configurazione immediata
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Chiave non valida: {e}")

# --- FUNZIONE AI (GEMINI 1.5 FLASH) ---
def get_ai(prompt):
    try:
        # Usiamo Flash che è veloce e sicuro
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE AI: {str(e)}"

# --- DIZIONARIO TRADUZIONI ---
trans = {
    "Italiano": {"nav":"Menu", "home":"🏠 Home", "cv":"📄 CV", "foto":"📸 Foto", "gen":"Genera", "up":"Carica PDF", "dl":"Scarica"},
    "English": {"nav":"Menu", "home":"🏠 Home", "cv":"📄 CV", "foto":"📸 Photo", "gen":"Generate", "up":"Upload PDF", "dl":"Download"},
    "Deutsch": {"nav":"Menü", "home":"🏠 Start", "cv":"📄 CV", "foto":"📸 Foto", "gen":"Erstellen", "up":"PDF Laden", "dl":"Laden"},
    "Espagnol": {"nav":"Menú", "home":"🏠 Inicio", "cv":"📄 CV", "foto":"📸 Foto", "gen":"Generar", "up":"Subir PDF", "dl":"Descargar"},
    "Português": {"nav":"Menu", "home":"🏠 Início", "cv":"📄 CV", "foto":"📸 Foto", "gen":"Gerar", "up":"Enviar PDF", "dl":"Baixar"}
}
t = trans[lang]

# --- NAVIGAZIONE ---
page = st.sidebar.radio(t["nav"], [t["home"], t["cv"], t["foto"]])

# --- PAGINA HOME ---
if page == t["home"]:
    st.title("Global Career Coach 🚀")
    st.write("Il tuo assistente professionale AI.")
    st.success("✅ Sistema Online. Seleziona una funzione dal menu a sinistra.")

# --- PAGINA CV ---
elif page == t["cv"]:
    st.header(t["cv"])
    uploaded_file = st.file_uploader(t["up"], type=["pdf"])
    
    if uploaded_file and st.button(t["gen"]):
        try:
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            with st.spinner("L'AI sta lavorando..."):
                res = get_ai(f"Riscrivi questo CV in modo professionale in {lang}:\n{text}")
                
                # Creazione Word
                doc = Document()
                doc.add_heading('Curriculum Vitae', 0)
                for line in res.split('\n'):
                    if line.strip(): doc.add_paragraph(line)
                bio = io.BytesIO()
                doc.save(bio)
                
                st.success("Fatto!")
                st.download_button(t["dl"], bio.getvalue(), "CV.docx")
                
        except Exception as e:
            st.error(f"Errore: {e}")

# --- PAGINA FOTO ---
elif page == t["foto"]:
    st.header(t["foto"])
    img = st.file_uploader("Upload", type=["jpg", "png"])
    if img:
        b = st.slider("Bordo", 0, 50, 10)
        i = Image.open(img)
        ni = ImageOps.expand(i, border=b, fill='white')
        st.image(ni, width=300)
