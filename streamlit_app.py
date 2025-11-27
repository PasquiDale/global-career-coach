import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
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
        background-color: #333333;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #555;
    }
</style>
""", unsafe_allow_html=True)

# --- AUTO-LOGIN ---
api_key = st.secrets.get("GEMINI_API_KEY", None)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
    st.title("Career Coach")
    lang = st.selectbox("Lingua / Language", ["Deutsch", "Italiano", "English", "Español", "Português"])
    st.divider()
    
    if not api_key:
        api_key = st.text_input("API Key", type="password")

    if api_key:
        try:
            genai.configure(api_key=api_key)
        except: pass

if not api_key:
    st.warning("⚠️ API Key mancante / Missing API Key")
    st.stop()

# --- WORD XML HACKS ---
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
    return text.replace("**", "").replace("###", "").replace("---", "").strip()

# --- AI ENGINE ---
def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- LOCALIZZAZIONE ---
loc = {
    "Deutsch": {
        "step1": "1. Foto hochladen", "step2": "2. Lebenslauf (PDF)", "gen": "CV Generieren", 
        "load": "Analyse läuft...", "bord": "Rahmenbreite", "dl_btn": "Word Herunterladen", 
        "preview": "Vorschau", "done": "Fertig!",
        "p_header": "Extrahiere NUR: Vorname Nachname | Adresse | Telefon | E-Mail. Format: Name | Adresse | Tel | Email.",
        "p_body": "Schreibe den CV auf DEUTSCH neu. Entferne Kontaktdaten. Nutze GROSSBUCHSTABEN für Titel."
    },
    "Italiano": {
        "step1": "1. Carica Foto", "step2": "2. Carica CV (PDF)", "gen": "Genera CV", 
        "load": "Analisi in corso...", "bord": "Spessore Bordo", "dl_btn": "Scarica CV Word", 
        "preview": "Anteprima", "done": "Fatto!",
        "p_header": "Estrai SOLO: Nome Cognome | Indirizzo | Telefono | Email. Formato: Nome | Indirizzo | Tel | Email.",
        "p_body": "Riscrivi il CV in ITALIANO. Rimuovi contatti. Usa MAIUSCOLO per i titoli."
    },
    "English": {
        "step1": "1. Upload Photo", "step2": "2. Upload CV (PDF)", "gen": "Generate CV", 
        "load": "Processing...", "bord": "Border Width", "dl_btn": "Download Word", 
        "preview": "Preview", "done": "Done!",
        "p_header": "Extract ONLY: Name Surname | Address | Phone | Email.",
        "p_body": "Rewrite CV in ENGLISH. Remove contacts. Use UPPERCASE for titles."
    },
    "Español": {
        "step1": "1. Subir Foto", "step2": "2. Subir CV", "gen": "Generar CV", 
        "load": "Procesando...", "bord": "Grosor Borde", "dl_btn": "Descargar Word", 
        "preview": "Vista Previa", "done": "¡Hecho!",
        "p_header": "Extrae SOLO: Nombre Apellido | Dirección | Teléfono | Email.",
        "p_body": "Reescribe en ESPAÑOL. Elimina contactos. Usa MAYÚSCULAS para títulos."
    },
    "Português": {
        "step1": "1. Enviar Foto", "step2": "2. Enviar CV", "gen": "Gerar CV", 
        "load": "Processando...", "bord": "Borda", "dl_btn": "Baixar Word", 
        "preview": "Visualização", "done": "Pronto!",
        "p_header": "Extraia APENAS: Nome Sobrenome | Endereço | Telefone | Email.",
        "p_body": "Reescreva em PORTUGUÊS. Remova contatos. Use MAIÚSCULAS para títulos."
    }
}
t = loc[lang]

# === INTERFACCIA ===
st.title("Global Career Coach 🚀")

# STEP 1
st.subheader(t["step1"])
c1, c2 = st.columns([1, 2])
with c1:
    f_img = st.file_uploader("Foto", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    border_val = st.slider(t["bord"], 0, 50, 15)

proc_img = None
with c2:
    if f_img:
        pil_img = Image.open(f_img)
        proc_img = ImageOps.expand(pil_img, border=border_val, fill='white')
        buf = io.BytesIO()
        proc_img.save(buf, format="JPEG")
        b64_img = base64.b64encode(buf.getvalue()).decode()
        st.markdown(f"""<div class="photo-preview"><span style="color:#ddd">{t['preview']}</span><br><br><img src="data:image/jpeg;base64,{b64_img}" width="180" style="border-radius:2px;"></div>""", unsafe_allow_html=True)

st.divider()

# STEP 2
st.subheader(t["step2"])
f_pdf = st.file_uploader("CV", type=["pdf"], label_visibility="collapsed")

if st.button(t["gen"], type="primary"):
    if not f_pdf:
        st.error("PDF Missing!")
    else:
        try:
            reader = pypdf.PdfReader(f_pdf)
            txt_in = ""
            for p in reader.pages: txt_in += p.extract_text()
            
            with st.spinner(t["load"]):
                # HEADER DATA
                h_prompt = f"{t['p_header']}\nTEXT: {txt_in[:1000]}"
                h_data = get_ai(h_prompt).strip()
                
                # BODY CONTENT
                b_prompt = f"{t['p_body']}\nTEXT: {txt_in}"
                b_content = clean_text(get_ai(b_prompt))
                
                # WORD DOC
                doc = Document()
                section = doc.sections[0]
                section.top_margin = Cm(1.0)
                section.left_margin = Cm(1.8)
                section.right_margin = Cm(1.8)
                
                BANNER_COLOR = "2c5f85" # Blu Professional

                if proc_img:
                    tbl = doc.add_table(rows=1, cols=2)
                    tbl.columns[0].width = Cm(4.5)
                    tbl.columns[1].width = Cm(14)
                    c_img, c_txt = tbl.cell(0,0), tbl.cell(0,1)
                    set_cell_bg(c_img, BANNER_COLOR)
                    set_cell_bg(c_txt, BANNER_COLOR)
                    
                    p = c_img.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    ib = io.BytesIO()
                    proc_img.save(ib, format='JPEG')
                    run.add_picture(ib, width=Cm(3.8))
                else:
                    tbl = doc.add_table(rows=1, cols=1)
                    c_txt = tbl.cell(0,0)
                    set_cell_bg(c_txt, BANNER_COLOR)

                parts = h_data.split('|')
                name = parts[0].strip() if len(parts)>0 else "Name"
                address = parts[1].strip() if len(parts)>1 else ""
                contacts = " • ".join([x.strip() for x in parts[2:]])

                c_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                
                p1 = c_txt.paragraphs[0]
                if not proc_img: p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r1 = p1.add_run(name)
                r1.font.size = Pt(26)
                r1.font.color.rgb = RGBColor(255,255,255)
                r1.bold = True
                
                p2 = c_txt.add_paragraph()
                if not proc_img: p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p2.paragraph_format.space_before = Pt(2)
                r2 = p2.add_run(address)
                r2.font.size = Pt(11)
                r2.font.color.rgb = RGBColor(240,240,240)
                
                p3 = c_txt.add_paragraph()
                if not proc_img: p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r3 = p3.add_run(contacts)
                r3.font.size = Pt(11)
                r3.font.color.rgb = RGBColor(240,240,240)
                r3.bold = True

                doc.add_paragraph().space_after = Pt(10)
                
                for line in b_content.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    if len(line)<60 and line.isupper() and any(c.isalpha() for c in line) and "@" not in line:
                        p = doc.add_paragraph()
                        p.space_before = Pt(14)
                        p.space_after = Pt(4)
                        add_bottom_border(p)
                        run = p.add_run(line)
                        run.bold = True
                        run.font.size = Pt(13)
                        run.font.color.rgb = RGBColor(44, 95, 133)
                    else:
                        p = doc.add_paragraph(line)
                        p.runs[0].font.size = Pt(11)
                        p.runs[0].font.name = 'Calibri'

                bio = io.BytesIO()
                doc.save(bio)
                st.balloons()
                st.success(f"✅ {t['done']}")
                st.download_button(t["dl_btn"], bio.getvalue(), f"CV_{lang}.docx")

        except Exception as e:
            st.error(f"Error: {e}")
