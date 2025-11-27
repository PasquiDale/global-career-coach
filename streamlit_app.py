import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach", page_icon="🚀", layout="wide")

# --- CSS ---
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- LOGIN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
    st.title("Career Coach")
    lang = st.selectbox("Lingua / Language", ["Deutsch", "Italiano", "English", "Español", "Português"])
    st.divider()
    api_key = st.text_input("API Key (AI Studio)", type="password")

    if api_key:
        try:
            genai.configure(api_key=api_key)
        except:
            pass

# --- FUNZIONE AI (GEMINI 3 PRO) ---
def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE: {str(e)}"

# --- FUNZIONE PULIZIA ---
def clean_text(text):
    return text.replace("**", "").replace("###", "").replace("---", "").replace("##", "")

# --- FUNZIONE BORDO SOTTO I TITOLI (Magia XML) ---
def add_bottom_border(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single') # Tipo di linea
    bottom.set(qn('w:sz'), '6')       # Spessore (1/8 pt)
    bottom.set(qn('w:space'), '1')    # Spazio
    bottom.set(qn('w:color'), 'auto') # Colore (Nero/Automatico)
    pbdr.append(bottom)
    pPr.append(pbdr)

# --- TRADUZIONI ---
trans = {
    "Deutsch": {"cv":"📄 CV & Foto", "up":"PDF Laden", "gen":"CV Optimieren", "dl":"CV Word Laden", "foto":"Fotostudio", "load":"Wir bearbeiten Ihr Dokument...", "done":"Fertig!"},
    "Italiano": {"cv":"📄 CV & Foto", "up":"Carica PDF", "gen":"Riformatta CV", "dl":"Scarica CV Word", "foto":"Studio Foto", "load":"Elaborazione...", "done":"Fatto!"},
    "English": {"cv":"📄 CV & Photo", "up":"Upload PDF", "gen":"Reformat CV", "dl":"Download Word", "foto":"Photo Studio", "load":"Processing...", "done":"Done!"},
    "Español": {"cv":"📄 CV & Foto", "up":"Subir PDF", "gen":"Reformatear CV", "dl":"Descargar Word", "foto":"Estudio Foto", "load":"Procesando...", "done":"¡Hecho!"},
    "Português": {"cv":"📄 CV & Foto", "up":"Enviar PDF", "gen":"Reformatar CV", "dl":"Baixar Word", "foto":"Estúdio Foto", "load":"Processando...", "done":"Pronto!"}
}
t = trans[lang]

# --- NAVIGAZIONE ---
page = st.sidebar.radio("Menu", ["🏠 Home", t["cv"], t["foto"]])

# --- HOME ---
if page == "🏠 Home":
    st.title("Global Career Coach 🚀")
    st.info("Professional AI System Ready.")

# --- CV ---
elif page == t["cv"]:
    st.header(t["cv"])
    if not api_key: st.warning("API Key?"); st.stop()
    
    f = st.file_uploader(t["up"], type=["pdf"])
    
    if f and st.button(t["gen"]):
        try:
            reader = pypdf.PdfReader(f)
            txt = ""
            for p in reader.pages: txt += p.extract_text()
            
            with st.spinner(t["load"]):
                # Prompt ottimizzato per struttura chiara
                prompt = f"""
                Sei un esperto HR. Riscrivi questo CV in {lang}.
                
                REGOLE DI FORMATTAZIONE RIGIDE:
                1. Prima riga: SOLO Nome e Cognome (nient'altro).
                2. Seconda riga: Dati di contatto su una riga.
                3. Per ogni sezione (es. PROFILO, ESPERIENZA, FORMAZIONE), scrivi il TITOLO tutto in MAIUSCOLO su una riga da solo.
                4. Sotto il titolo scrivi il contenuto.
                5. NON usare markdown (** o ##).
                6. Sii professionale e sintetico.
                
                TESTO ORIGINALE:
                {txt}
                """
                
                res = get_ai(prompt)
                res_clean = clean_text(res)
                
                if "ERRORE" in res:
                    st.error(res)
                else:
                    # --- COSTRUZIONE WORD ---
                    doc = Document()
                    
                    lines = res_clean.split('\n')
                    
                    # 1. Nome (Gigante)
                    if lines:
                        head = doc.add_heading(lines[0].strip(), 0)
                        head.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        head.runs[0].font.color.rgb = RGBColor(0, 51, 102) # Blu scuro
                    
                    # 2. Resto del documento
                    for line in lines[1:]:
                        line = line.strip()
                        if not line: continue
                        
                        # Riconoscimento Titoli di Sezione (Corti e MAIUSCOLI)
                        # Es: "ESPERIENZA PROFESSIONALE"
                        if len(line) < 50 and line.isupper() and any(c.isalpha() for c in line):
                            p = doc.add_paragraph()
                            add_bottom_border(p) # AGGIUNGE LA RIGA SOTTO!
                            runner = p.add_run(line)
                            runner.bold = True
                            runner.font.size = Pt(14)
                            runner.font.color.rgb = RGBColor(0, 51, 102) # Blu scuro
                            p.space_before = Pt(12)
                            p.space_after = Pt(6)
                        else:
                            # Testo normale
                            p = doc.add_paragraph(line)
                            p.paragraph_format.space_after = Pt(4)
                            runner = p.runs[0]
                            runner.font.size = Pt(11)
                            runner.font.name = 'Calibri'

                    bio = io.BytesIO()
                    doc.save(bio)
                    
                    st.success(t["done"])
                    st.download_button(t["dl"], bio.getvalue(), "CV_Pro.docx")
                    
        except Exception as e:
            st.error(f"Errore: {e}")

# --- FOTO ---
elif page == t["foto"]:
    st.header(t["foto"])
    img = st.file_uploader("Upload", type=["jpg", "png"])
    if img:
        col1, col2 = st.columns(2)
        b = st.slider("Bordo/Border", 0, 50, 15)
        i = Image.open(img)
        ni = ImageOps.expand(i, border=b, fill='white')
        with col1: st.image(img, width=150, caption="Original")
        with col2: st.image(ni, width=150, caption="Result")
        buf = io.BytesIO()
        ni.save(buf, format="JPEG")
        st.download_button("Download", buf.getvalue(), "foto.jpg", "image/jpeg")
