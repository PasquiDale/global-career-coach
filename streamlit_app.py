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

# --- CSS (UI PULITA) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    .photo-preview {
        background-color: #2b2b2b;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #555;
    }
    .stFileUploader label { display: none; }
    .upload-label { font-size: 18px; font-weight: bold; margin-bottom: 5px; }
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

# --- FUNZIONI UTILITY WORD ---
def set_cell_bg(cell, color_hex):
    """Imposta il colore di sfondo di una cella"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_bottom_border(paragraph):
    """Aggiunge una linea sotto il paragrafo"""
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

def clean_ai_text(text):
    """Pulisce markdown e simboli indesiderati"""
    return text.replace("**", "").replace("###", "").replace("---", "").strip()

def clean_field(text):
    """Rimuove etichette come 'Nome:', 'Name:', ecc."""
    bad_prefixes = ["Nome:", "Name:", "Cognome:", "Surname:", "Indirizzo:", "Address:", "Email:", "Tel:", "Phone:", "**"]
    for prefix in bad_prefixes:
        text = text.replace(prefix, "")
    return text.strip()

# --- AI ENGINE ---
def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # Flash è ottimo per task veloci
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- TRADUZIONI ---
trans = {
    "Deutsch": {
        "step1": "1. Foto", "step2": "2. Lebenslauf (PDF)", 
        "gen": "CV Generieren (Word)", "load": "Erstelle Word-Datei...", "bord": "Rahmen", 
        "dl_btn": "Word Herunterladen", "preview": "Vorschau", "done": "Fertig!", 
        "txt_up": "PDF hier hochladen", "txt_img": "Foto hier hochladen"
    },
    "Italiano": {
        "step1": "1. Foto", "step2": "2. CV (PDF)", 
        "gen": "Genera CV (Word)", "load": "Creazione Word in corso...", "bord": "Bordo", 
        "dl_btn": "Scarica Word", "preview": "Anteprima", "done": "Fatto!", 
        "txt_up": "Carica PDF qui", "txt_img": "Carica Foto qui"
    },
    "English": {
        "step1": "1. Photo", "step2": "2. CV (PDF)", 
        "gen": "Generate CV (Word)", "load": "Creating Word Doc...", "bord": "Border", 
        "dl_btn": "Download Word", "preview": "Preview", "done": "Done!", 
        "txt_up": "Upload PDF here", "txt_img": "Upload Photo here"
    },
    "Español": {
        "step1": "1. Foto", "step2": "2. CV (PDF)", 
        "gen": "Generar CV (Word)", "load": "Creando Word...", "bord": "Borde", 
        "dl_btn": "Descargar Word", "preview": "Vista Previa", "done": "¡Hecho!", 
        "txt_up": "Sube PDF aquí", "txt_img": "Sube Foto aquí"
    },
    "Português": {
        "step1": "1. Foto", "step2": "2. CV (PDF)", 
        "gen": "Gerar CV (Word)", "load": "Criando Word...", "bord": "Borda", 
        "dl_btn": "Baixar Word", "preview": "Visualização", "done": "Pronto!", 
        "txt_up": "Envie PDF aqui", "txt_img": "Envie Foto aqui"
    }
}
t = trans.get(lang, trans["English"])

# === INTERFACCIA ===
st.title("Global Career Coach 🚀")

# STEP 1: FOTO
st.subheader(t["step1"])
c1, c2 = st.columns([1, 2])
with c1:
    st.markdown(f"<div class='upload-label'>{t['txt_img']}</div>", unsafe_allow_html=True)
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
st.subheader(t["step2"])
st.markdown(f"<div class='upload-label'>{t['txt_up']}</div>", unsafe_allow_html=True)
f_pdf = st.file_uploader("Upload2", type=["pdf"], label_visibility="collapsed")

# --- GENERAZIONE ---
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
                h_prompt = f"""
                You are a data extraction engine.
                Extract these fields from the text. Return ONLY the values separated by | pipe.
                Format: FirstName LastName|Address|PhoneNumber|EmailAddress
                If a field is missing, leave it empty but keep the pipe.
                NO LABELS like "Name:". Just the data.
                
                TEXT: {txt_in[:1500]}
                """
                h_data = get_ai(h_prompt).strip()
                
                # 2. BODY CONTENT
                b_prompt = f"""
                Act as a Professional Resume Writer. Rewrite the resume in {lang}.
                INSTRUCTIONS:
                1. DO NOT include the Header info (Name, Address, Phone, Email) - I will handle it.
                2. Start immediately with the Professional Summary or Experience.
                3. Use UPPERCASE for Section Titles (e.g. EXPERIENCE, EDUCATION).
                4. Do NOT use markdown bold/italic (no **, no _).
                5. Keep it professional and concise.
                
                TEXT: {txt_in}
                """
                b_content = clean_ai_text(get_ai(b_prompt))

                # --- WORD DOCUMENT CONSTRUCTION ---
                doc = Document()
                
                # Setup Margini
                section = doc.sections[0]
                section.top_margin = Cm(1.0)
                section.left_margin = Cm(1.5)
                section.right_margin = Cm(1.5)
                
                BANNER_COLOR = "1F4E79" # Blu Professional

                # --- HEADER TABLE (Banner) ---
                if proc_img:
                    tbl = doc.add_table(rows=1, cols=2)
                    tbl.columns[0].width = Cm(4.0)  # Colonna Foto
                    tbl.columns[1].width = Cm(14.5) # Colonna Testo
                    c_img, c_txt = tbl.cell(0,0), tbl.cell(0,1)
                    
                    # Colora sfondo
                    set_cell_bg(c_img, BANNER_COLOR)
                    set_cell_bg(c_txt, BANNER_COLOR)
                    
                    # Inserimento Foto
                    c_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    p_img = c_img.paragraphs[0]
                    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    # Padding manuale
                    p_img.paragraph_format.space_before = Pt(6)
                    p_img.paragraph_format.space_after = Pt(6)
                    
                    run = p_img.add_run()
                    ib = io.BytesIO()
                    proc_img.save(ib, format='JPEG')
                    run.add_picture(ib, width=Cm(3.5))
                else:
                    tbl = doc.add_table(rows=1, cols=1)
                    c_txt = tbl.cell(0,0)
                    set_cell_bg(c_txt, BANNER_COLOR)

                # Parsing Dati
                parts = h_data.split('|')
                name = clean_field(parts[0]) if len(parts)>0 else "Name"
                address = clean_field(parts[1]) if len(parts)>1 else ""
                tel = clean_field(parts[2]) if len(parts)>2 else ""
                email = clean_field(parts[3]) if len(parts)>3 else ""
                
                contact_line = f"{tel}  •  {email}"

                # Testo Banner
                c_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                
                # Nome
                p1 = c_txt.paragraphs[0]
                if not proc_img: p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r1 = p1.add_run(name)
                r1.font.size = Pt(24)
                r1.font.color.rgb = RGBColor(255,255,255)
                r1.bold = True
                p1.paragraph_format.space_after = Pt(2)
                
                # Indirizzo
                p2 = c_txt.add_paragraph()
                if not proc_img: p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r2 = p2.add_run(address)
                r2.font.size = Pt(10)
                r2.font.color.rgb = RGBColor(230,230,230)
                p2.paragraph_format.space_after = Pt(0)
                
                # Contatti
                p3 = c_txt.add_paragraph()
                if not proc_img: p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r3 = p3.add_run(contact_line)
                r3.font.size = Pt(10)
                r3.font.color.rgb = RGBColor(230,230,230)
                r3.bold = True

                # Spazio sotto il banner
                doc.add_paragraph().space_after = Pt(12)
                
                # --- BODY ---
                for line in b_content.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    # Controllo Titoli (Maiuscolo, Corto, No caratteri strani)
                    if len(line)<50 and line.isupper() and any(c.isalpha() for c in line) and "@" not in line:
                        p = doc.add_paragraph()
                        p.space_before = Pt(14)
                        p.space_after = Pt(4)
                        add_bottom_border(p) # Linea sotto
                        run = p.add_run(line)
                        run.bold = True
                        run.font.size = Pt(12)
                        run.font.color.rgb = RGBColor(31, 78, 121) # Blu scuro
                    else:
                        p = doc.add_paragraph(line)
                        p.runs[0].font.size = Pt(11)
                        p.runs[0].font.name = 'Calibri'

                # Salvataggio in RAM
                bio = io.BytesIO()
                doc.save(bio)
                
                st.balloons()
                st.success(f"✅ {t['done']}")
                
                # TASTO DOWNLOAD WORD
                st.download_button(
                    label=t["dl_btn"],
                    data=bio.getvalue(),
                    file_name=f"CV_{name.replace(' ','_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

        except Exception as e:
            st.error(f"Error: {e}")
