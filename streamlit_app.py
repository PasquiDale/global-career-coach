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

# --- CSS AVANZATO (Sovrascrittura Interfaccia) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    
    /* Box Anteprima Foto */
    .photo-preview {
        background-color: #2b2b2b;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #555;
    }
    
    /* Nascondiamo completamente il testo standard di Streamlit uploader */
    [data-testid='stFileUploader'] section {
        padding: 20px;
    }
    [data-testid='stFileUploader'] section > div {
        padding-top: 10px;
    }
    /* Nascondiamo la label piccola */
    .stFileUploader label {
        display: none;
    }
    /* Etichette personalizzate grandi */
    .custom-label {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 8px;
        display: block;
        color: #333;
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
    st.warning("⚠️ API Key mancante.")
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
    bottom.set(qn('w:color'), '2c5f85')
    pbdr.append(bottom)
    pPr.append(pbdr)

def clean_text(text):
    return text.replace("**", "").replace("###", "").replace("---", "").strip()

def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- TRADUZIONI ---
trans = {
    "Deutsch": {
        "step1": "1. Foto hochladen", "step2": "2. Lebenslauf (PDF) hochladen", 
        "gen": "CV Generieren", "load": "Design wird erstellt...", "bord": "Rahmen", 
        "dl_btn": "Word Herunterladen", "preview": "Vorschau", "done": "Fertig!", 
        "txt_up": "Klicken Sie hier, um das PDF hochzuladen", "txt_img": "Klicken Sie hier, um das Foto hochzuladen"
    },
    "Italiano": {
        "step1": "1. Carica Foto", "step2": "2. Carica CV (PDF)", 
        "gen": "Genera CV", "load": "Creazione Design...", "bord": "Bordo", 
        "dl_btn": "Scarica Word", "preview": "Anteprima", "done": "Fatto!", 
        "txt_up": "Clicca qui per caricare il PDF", "txt_img": "Clicca qui per caricare la Foto"
    },
    "English": {
        "step1": "1. Upload Photo", "step2": "2. Upload CV (PDF)", 
        "gen": "Generate CV", "load": "Creating Design...", "bord": "Border", 
        "dl_btn": "Download Word", "preview": "Preview", "done": "Done!", 
        "txt_up": "Click here to upload PDF", "txt_img": "Click here to upload Photo"
    },
    "Español": {
        "step1": "1. Subir Foto", "step2": "2. Subir CV", 
        "gen": "Generar CV", "load": "Creando...", "bord": "Borde", 
        "dl_btn": "Descargar Word", "preview": "Vista Previa", "done": "¡Hecho!", 
        "txt_up": "Clic aquí para subir PDF", "txt_img": "Clic aquí para subir Foto"
    },
    "Português": {
        "step1": "1. Enviar Foto", "step2": "2. Enviar CV", 
        "gen": "Gerar CV", "load": "Criando...", "bord": "Borda", 
        "dl_btn": "Baixar Word", "preview": "Visualização", "done": "Pronto!", 
        "txt_up": "Clique aqui para enviar PDF", "txt_img": "Clique aqui para enviar Foto"
    }
}
t = trans[lang]

# === INTERFACCIA ===
st.title("Global Career Coach 🚀")

# STEP 1: FOTO
c1, c2 = st.columns([1, 2])
with c1:
    st.markdown(f"<div class='custom-label'>{t['step1']}</div>", unsafe_allow_html=True)
    st.caption(t['txt_img'])
    f_img = st.file_uploader("Upload1", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    border_val = st.slider(t["bord"], 0, 50, 15)

proc_img = None
with c2:
    if f_img:
        pil_img = Image.open(f_img)
        proc_img = ImageOps.expand(pil_img, border=border_val, fill='white')
        buf = io.BytesIO()
        proc_img.save(buf, format="JPEG")
        b64_img = base64.b64encode(buf.getvalue()).decode()
        st.markdown(f"""<div class="photo-preview"><span style="color:#ddd">{t['preview']}</span><br><br><img src="data:image/jpeg;base64,{b64_img}" width="150" style="border-radius:2px;"></div>""", unsafe_allow_html=True)

st.divider()

# STEP 2: PDF
st.markdown(f"<div class='custom-label'>{t['step2']}</div>", unsafe_allow_html=True)
st.caption(t['txt_up'])
f_pdf = st.file_uploader("Upload2", type=["pdf"], label_visibility="collapsed")

if st.button(t["gen"], type="primary"):
    if not f_pdf:
        st.error("PDF Missing!")
    else:
        try:
            reader = pypdf.PdfReader(f_pdf)
            txt_in = ""
            for p in reader.pages: txt_in += p.extract_text()
            
            with st.spinner(t["load"]):
                # 1. HEADER DATA
                h_prompt = f"Estrai: Nome Cognome | Indirizzo | Telefono | Email.\nTESTO: {txt_in[:2000]}"
                h_data = get_ai(h_prompt).strip()
                
                # 2. BODY CONTENT
                b_prompt = f"""
                Sei un esperto HR. Riscrivi il CV in {lang}.
                REGOLE:
                1. NO frasi introduttive.
                2. NO dati di contatto (già nel banner).
                3. TITOLI MAIUSCOLI.
                TESTO: {txt_in}
                """
                b_content = clean_text(get_ai(b_prompt))

                # --- WORD GENERATION ---
                doc = Document()
                section = doc.sections[0]
                section.top_margin = Cm(1.0)
                section.left_margin = Cm(1.5)
                section.right_margin = Cm(1.5)
                
                BANNER_COLOR = "2c5f85"

                if proc_img:
                    tbl = doc.add_table(rows=1, cols=2)
                    tbl.columns[0].width = Cm(4.0)
                    tbl.columns[1].width = Cm(14.5)
                    c_img, c_txt = tbl.cell(0,0), tbl.cell(0,1)
                    set_cell_bg(c_img, BANNER_COLOR)
                    set_cell_bg(c_txt, BANNER_COLOR)
                    
                    # --- FOTO CENTRATA CON PADDING ---
                    c_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    p_img = c_img.paragraphs[0]
                    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    
                    # QUI STA LA MAGIA DEL MARGINE
                    p_img.paragraph_format.space_before = Pt(10) # Spazio SOPRA la foto (dentro il blu)
                    p_img.paragraph_format.space_after = Pt(10)  # Spazio SOTTO la foto (dentro il blu)
                    
                    run = p_img.add_run()
                    ib = io.BytesIO()
                    proc_img.save(ib, format='JPEG')
                    run.add_picture(ib, width=Cm(3.8))
                else:
                    tbl = doc.add_table(rows=1, cols=1)
                    c_txt = tbl.cell(0,0)
                    set_cell_bg(c_txt, BANNER_COLOR)

                # DATI
                parts = h_data.split('|')
                name = parts[0].strip() if len(parts)>0 else "Name"
                addr = parts[1].strip() if len(parts)>1 else ""
                tel = parts[2].strip() if len(parts)>2 else ""
                email = parts[3].strip() if len(parts)>3 else ""
                contact_line = f"{tel}  •  {email}"

                # TESTO BANNER
                c_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                
                p1 = c_txt.paragraphs[0]
                if not proc_img: p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r1 = p1.add_run(name)
                r1.font.size = Pt(26)
                r1.font.color.rgb = RGBColor(255,255,255)
                r1.bold = True
                p1.paragraph_format.space_after = Pt(2) 
                
                p2 = c_txt.add_paragraph()
                if not proc_img: p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r2 = p2.add_run(addr)
                r2.font.size = Pt(11)
                r2.font.color.rgb = RGBColor(230,230,230)
                p2.paragraph_format.space_after = Pt(0)
                
                p3 = c_txt.add_paragraph()
                if not proc_img: p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r3 = p3.add_run(contact_line)
                r3.font.size = Pt(11)
                r3.font.color.rgb = RGBColor(230,230,230)
                r3.bold = True

                doc.add_paragraph().space_after = Pt(10)
                
                for line in b_content.split('\n'):
                    line = line.strip()
                    if not line: continue
                    if name in line or email in line: continue 

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
