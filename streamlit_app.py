import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
import base64
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach Pro", page_icon="🚀", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    .photo-preview {
        background-color: #2b2b2b;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGICA CHIAVE AUTOMATICA ---
# 1. Cerca nei Secrets
api_key = st.secrets.get("GEMINI_API_KEY", None)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
    st.title("Career Coach")
    lang = st.selectbox("Lingua / Language", ["Italiano", "Deutsch", "English", "Español", "Português"])
    st.divider()
    
    # 2. Se NON c'è nei Secrets, chiedila a mano
    if not api_key:
        api_key = st.text_input("Inserisci API Key", type="password")

    # Configura subito se la chiave esiste
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except: pass

# Blocco se manca la chiave
if not api_key:
    st.warning("⬅️ Chiave API non trovata. Inseriscila nel menu a sinistra.")
    st.stop()

# --- FUNZIONI WORD ---
def set_cell_bg(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_bottom_border(paragraph):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pbdr.append(bottom)
    pPr.append(pbdr)

def clean_text(text):
    return text.replace("**", "").replace("###", "").replace("---", "")

# --- FUNZIONE AI (GEMINI 3 PRO) ---
def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE: {str(e)}"

# --- TRADUZIONI ---
trans = {
    "Italiano": {"step1":"1. Carica la tua Foto", "step2":"2. Carica il tuo CV (PDF)", "gen":"Genera CV Completo", "load":"Creazione CV e Design in corso...", "bord":"Spessore Bordo"},
    "Deutsch": {"step1":"1. Foto hochladen", "step2":"2. Lebenslauf (PDF) hochladen", "gen":"CV Generieren", "load":"Erstelle Design...", "bord":"Rand"},
    "English": {"step1":"1. Upload Photo", "step2":"2. Upload CV (PDF)", "gen":"Generate Full CV", "load":"Creating Design...", "bord":"Border Size"},
    "Español": {"step1":"1. Subir Foto", "step2":"2. Subir CV (PDF)", "gen":"Generar CV", "load":"Creando Diseño...", "bord":"Borde"},
    "Português": {"step1":"1. Enviar Foto", "step2":"2. Enviar CV (PDF)", "gen":"Gerar CV", "load":"Criando Design...", "bord":"Borda"}
}
t = trans.get(lang, trans["English"])

# === INTERFACCIA PRINCIPALE ===
st.title("Global Career Coach 🚀")

# --- STEP 1: FOTO ---
st.subheader(t["step1"])
col_img_in, col_img_prev = st.columns([1, 2])

with col_img_in:
    f_img = st.file_uploader("Foto (JPG/PNG)", type=["jpg", "png", "jpeg"])
    border_val = st.slider(t["bord"], 0, 50, 15)

processed_image = None 

with col_img_prev:
    if f_img:
        image_pil = Image.open(f_img)
        processed_image = ImageOps.expand(image_pil, border=border_val, fill='white')
        
        buffered = io.BytesIO()
        processed_image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        st.markdown(f"""
        <div class="photo-preview">
            <img src="data:image/jpeg;base64,{img_str}" width="200" style="border-radius:5px;">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Carica foto per anteprima.")

st.divider()

# --- STEP 2: PDF & GENERAZIONE ---
st.subheader(t["step2"])
f_pdf = st.file_uploader("CV (PDF)", type=["pdf"])

if st.button(t["gen"], type="primary"):
    if not f_pdf:
        st.error("Carica il PDF del CV.")
    else:
        try:
            reader = pypdf.PdfReader(f_pdf)
            txt_pdf = ""
            for p in reader.pages: txt_pdf += p.extract_text()
            
            with st.spinner(t["load"]):
                # 2. ESTRAZIONE DATI
                prompt_header = f"""
                Estrai i dati di contatto. Formato ESATTO:
                Nome Cognome | Indirizzo | Telefono | Email
                TESTO: {txt_pdf[:1500]}
                """
                header_data = get_ai(prompt_header).strip()
                
                # 3. RISCRITTURA CORPO
                prompt_body = f"""
                Sei un esperto HR. Riscrivi il CV in {lang}.
                NON includere intestazione (Nome, Contatti).
                Usa titoli MAIUSCOLI per le sezioni.
                Sii professionale. Niente markdown.
                TESTO: {txt_pdf}
                """
                body_content = clean_text(get_ai(prompt_body))

                # --- WORD BUILDER ---
                doc = Document()
                section = doc.sections[0]
                section.top_margin = Cm(1.0)
                section.left_margin = Cm(1.5)
                section.right_margin = Cm(1.5)

                # BANNER
                if processed_image:
                    table = doc.add_table(rows=1, cols=2)
                    table.columns[0].width = Cm(4.5) 
                    table.columns[1].width = Cm(14)
                    c_img = table.cell(0, 0)
                    c_txt = table.cell(0, 1)
                    set_cell_bg(c_img, "0E2F44")
                    set_cell_bg(c_txt, "0E2F44")
                    
                    p = c_img.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    img_buffer = io.BytesIO()
                    processed_image.save(img_buffer, format='JPEG')
                    run.add_picture(img_buffer, width=Cm(3.5))
                else:
                    table = doc.add_table(rows=1, cols=1)
                    c_txt = table.cell(0, 0)
                    set_cell_bg(c_txt, "0E2F44")

                # TESTO BANNER
                c_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                parts = header_data.split('|')
                name = parts[0].strip() if len(parts)>0 else "Nome Cognome"
                info = "  •  ".join([x.strip() for x in parts[1:]])
                
                p1 = c_txt.paragraphs[0]
                if not processed_image: p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r1 = p1.add_run(name)
                r1.font.size = Pt(24)
                r1.font.color.rgb = RGBColor(255,255,255)
                r1.bold = True
                
                p2 = c_txt.add_paragraph(info)
                if not processed_image: p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r2 = p2.add_run()
                r2.text = info
                r2.font.size = Pt(10)
                r2.font.color.rgb = RGBColor(230,230,230)

                doc.add_paragraph().space_after = Pt(12)

                # CORPO
                for line in body_content.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    if len(line)<60 and line.isupper() and any(c.isalpha() for c in line):
                        p = doc.add_paragraph()
                        p.space_before = Pt(12)
                        add_bottom_border(p)
                        run = p.add_run(line)
                        run.bold = True
                        run.font.size = Pt(12)
                        run.font.color.rgb = RGBColor(14, 47, 68)
                    else:
                        p = doc.add_paragraph(line)
                        p.runs[0].font.size = Pt(11)

                bio = io.BytesIO()
                doc.save(bio)
                st.success("✅ Documento Pronto!")
                st.download_button("Scarica CV Word", bio.getvalue(), "CV_Professional.docx")

        except Exception as e:
            st.error(f"Errore: {e}")
