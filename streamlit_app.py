import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach", page_icon="🚀", layout="wide")

# --- CSS (Nasconde menu e footer) ---
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
    st.title("Career Coach")
    lang = st.selectbox("Lingua", ["Italiano", "English", "Deutsch", "Español", "Português"])
    st.divider()
    st.markdown("### 🔐 Accesso")
    api_key = st.text_input("Inserisci API Key (AI Studio)", type="password")

    if api_key:
        try:
            genai.configure(api_key=api_key)
        except:
            pass

# --- FUNZIONE AI (GEMINI 3 PRO - POWER) ---
def get_ai(prompt):
    try:
        # Usiamo la versione 3 PRO che hai nel tuo account!
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE: {str(e)}"

# --- FUNZIONE PULIZIA TESTO ---
def clean_text(text):
    # Rimuove i simboli markdown che danno fastidio in Word
    return text.replace("**", "").replace("###", "").replace("---", "")

# --- TRADUZIONI ---
trans = {
    "Italiano": {"home":"🏠 Home", "cv":"📄 CV & Foto", "up":"Carica il tuo CV (PDF)", "gen":"Riformatta CV", "dl":"Scarica CV Word", "foto_tit":"Studio Foto", "up_f":"Carica Foto", "dl_f":"Scarica Foto"},
    "English": {"home":"🏠 Home", "cv":"📄 CV & Photo", "up":"Upload CV (PDF)", "gen":"Reformat CV", "dl":"Download Word CV", "foto_tit":"Photo Studio", "up_f":"Upload Photo", "dl_f":"Download Photo"},
    "Deutsch": {"home":"🏠 Start", "cv":"📄 CV & Foto", "up":"PDF Laden", "gen":"CV Optimieren", "dl":"CV Word Laden", "foto_tit":"Fotostudio", "up_f":"Foto laden", "dl_f":"Foto laden"},
    "Español": {"home":"🏠 Inicio", "cv":"📄 CV & Foto", "up":"Subir PDF", "gen":"Reformatear CV", "dl":"Descargar CV Word", "foto_tit":"Estudio Foto", "up_f":"Subir Foto", "dl_f":"Descargar Foto"},
    "Português": {"home":"🏠 Início", "cv":"📄 CV & Foto", "up":"Enviar PDF", "gen":"Reformatar CV", "dl":"Baixar CV Word", "foto_tit":"Estúdio Foto", "up_f":"Enviar Foto", "dl_f":"Baixar Foto"}
}
t = trans[lang]

# --- NAVIGAZIONE ---
page = st.sidebar.radio("Menu", [t["home"], t["cv"], t["foto_tit"]])

# --- HOME ---
if page == t["home"]:
    st.title("Global Career Coach 🚀")
    st.info(f"Powered by **Gemini 3 Pro**. Pronto all'uso.")

# --- CV ---
elif page == t["cv"]:
    st.header(t["cv"])
    
    if not api_key:
        st.warning("⬅️ Inserisci la chiave API a sinistra per iniziare.")
        st.stop()
        
    f = st.file_uploader(t["up"], type=["pdf"])
    
    if f and st.button(t["gen"]):
        try:
            reader = pypdf.PdfReader(f)
            txt = ""
            for p in reader.pages: txt += p.extract_text()
            
            with st.spinner("Gemini 3 Pro sta lavorando per te..."):
                # Prompt "Silenzioso" e Professionale
                prompt = f"""
                Agisci come un esperto HR internazionale. 
                Riscrivi questo CV in {lang}. 
                REGOLE FONDAMENTALI:
                1. NON scrivere frasi introduttive (tipo "Ecco il CV"). Inizia subito col Nome.
                2. Usa un linguaggio 'Action-Oriented' e professionale.
                3. Organizza bene le sezioni (Profilo, Esperienza, Istruzione).
                4. Non usare simboli markdown come ** o ##.
                
                TESTO CV ORIGINALE:
                {txt}
                """
                
                res = get_ai(prompt)
                res_clean = clean_text(res)
                
                if "ERRORE" in res:
                    st.error(res)
                else:
                    # --- CREAZIONE WORD MIGLIORATA ---
                    doc = Document()
                    
                    # Titolo (Nome del Candidato)
                    title = doc.add_heading('CURRICULUM VITAE', 0)
                    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    
                    for line in res_clean.split('\n'):
                        line = line.strip()
                        if line:
                            # Riconoscimento base dei titoli (se è corto e maiuscolo)
                            if len(line) < 40 and line.isupper() and ":" not in line:
                                p = doc.add_heading(line, level=1)
                                run = p.runs[0]
                                run.font.color.rgb = RGBColor(0, 51, 102) # Blu Scuro Professionale
                            else:
                                doc.add_paragraph(line)
                    
                    bio = io.BytesIO()
                    doc.save(bio)
                    
                    st.success("CV Pronto!")
                    st.download_button(t["dl"], bio.getvalue(), "CV_Pro_Gemini3.docx")
                    
        except Exception as e:
            st.error(f"Errore: {e}")

# --- FOTO ---
elif page == t["foto_tit"]:
    st.header(t["foto_tit"])
    img = st.file_uploader(t["up_f"], type=["jpg", "png"])
    if img:
        col1, col2 = st.columns(2)
        with col1:
            st.write("Originale")
            st.image(img, width=200)
            
        b = st.slider("Spessore Bordo Bianco", 0, 50, 15)
        
        i = Image.open(img)
        ni = ImageOps.expand(i, border=b, fill='white')
        
        with col2:
            st.write("Risultato")
            st.image(ni, width=200)
            
        buf = io.BytesIO()
        ni.save(buf, format="JPEG")
        st.download_button(t["dl_f"], buf.getvalue(), "Foto_CV.jpg", "image/jpeg")
