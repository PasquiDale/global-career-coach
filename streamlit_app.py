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

# --- AUTO-LOGIN (SECRETS) ---
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

# --- WORD XML HACKS (Design Avanzato) ---
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
    # Rimuove markdown e pulisce spazi extra
    return text.replace("**", "").replace("###", "").replace("---", "").strip()

# --- AI ENGINE (GEMINI 3 PRO) ---
def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- LOCALIZZAZIONE COMPLETA ---
# Qui definiamo tutto, anche i prompt per l'AI, così parla la lingua giusta.
loc = {
    "Deutsch": {
        "step1": "1. Foto hochladen", "step2": "2. Lebenslauf (PDF)", "gen": "CV Generieren", 
        "load": "Analyse läuft... Bitte warten.", "bord": "Rahmenbreite",
        "dl_btn": "Word-Datei Herunterladen", "preview": "Vorschau (Dunkler Hintergrund)",
        "p_header": "Extrahiere NUR: Vorname Nachname | Adresse | Telefon | E-Mail. Format: Name | Adresse | Tel | Email. Wenn etwas fehlt, leer lassen.",
        "p_body": "Du bist ein HR-Experte. Schreibe diesen Lebenslauf auf DEUTSCH neu. WICHTIG: Entferne ALLE Kontaktdaten und Namen (diese stehen im Banner). Nutze professionelle Sprache. Benutze GROSSBUCHSTABEN für Sektions-Titel.",
        "cv_title": "LEBENSLAUF"
    },
    "Italiano": {
        "step1": "1. Carica Foto", "step2": "2. Carica CV (PDF)", "gen": "Genera CV", 
        "load": "Analisi e scrittura in corso...", "bord": "Spessore Bordo",
        "dl_btn": "Scarica CV Word", "preview": "Anteprima (Sfondo Scuro)",
        "p_header": "Estrai SOLTANTO: Nome Cognome | Indirizzo | Telefono | Email. Formato: Nome | Indirizzo | Tel | Email. Non aggiungere altro.",
        "p_body": "Sei un esperto HR. Riscrivi il CV in ITALIANO. IMPORTANTE: RIMUOVI intestazione, nome e contatti (li metto nel banner). Usa un tono professionale. Usa MAIUSCOLO per i titoli delle sezioni.",
        "cv_title": "CURRICULUM VITAE"
    },
    "English": {
        "step1": "1. Upload Photo", "step2": "2. Upload CV (PDF)", "gen": "Generate CV", 
        "load": "Processing document...", "bord": "Border Width",
        "dl_btn": "Download Word Doc", "preview": "Preview (Dark Background)",
        "p_header": "Extract ONLY: Name Surname | Address | Phone | Email. Format: Name | Address | Phone | Email.",
        "p_body": "You are an HR Expert. Rewrite this CV in ENGLISH. IMPORTANT: REMOVE header, name and contacts (they go in the banner). Use professional tone. Use UPPERCASE for section titles.",
        "cv_title": "RESUME"
    },
    "Español": {
        "step1": "1. Subir Foto", "step2": "2. Subir CV (PDF)", "gen": "Generar CV", 
        "load": "Procesando...", "bord": "Grosor Borde",
        "dl_btn": "Descargar Word", "preview": "Vista Previa",
        "p_header": "Extrae SOLO: Nombre Apellido | Dirección | Teléfono | Email.",
        "p_body": "Eres experto RRHH. Reescribe en ESPAÑOL. IMPORTANTE: ELIMINA nombre y contactos del texto. Usa tono profesional y MAYÚSCULAS para títulos.",
        "cv_title": "CURRICULUM VITAE"
    },
    "Português": {
        "step1": "1. Enviar Foto", "step2": "2. Enviar CV (PDF)", "gen": "Gerar CV", 
        "load": "Processando...", "bord": "Borda",
        "dl_btn": "Baixar Word", "preview": "Visualização",
        "p_header": "Extraia APENAS: Nome Sobrenome | Endereço | Telefone | Email.",
        "p_body": "Você é especialista em RH. Reescreva em PORTUGUÊS. IMPORTANTE: REMOVA nome e contatos do texto. Use tom profissional e MAIÚSCULAS para títulos.",
        "cv_title": "CURRICULUM VITAE"
    }
}
t = loc[lang]

# === INTERFACCIA ===
st.title("Global Career Coach 🚀")

# STEP 1: FOTO
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
        
        # Anteprima Base64
        buf = io.BytesIO()
        proc_img.save(buf, format="JPEG")
        b64_img = base64.b64encode(buf.getvalue()).decode()
        
        st.markdown(f"""
        <div class="photo-preview">
            <span style="color:#ddd; font-size:0.8em">{t['preview']}</span><br><br>
            <img src="data:image/jpeg;base64,{b64_img}" width="180" style="border-radius:2px; box-shadow: 0px 4px 10px rgba(0,0,0,0.5);">
        </div>
        """, unsafe_allow_html=True)

st.divider()

# STEP 2: PDF
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
                # 1. HEADER DATA
                h_prompt = f"{t['p_header']}\nTEXT: {txt_in[:1000]}"
                h_data = get_ai(h_prompt).strip()
                
                # 2. BODY CONTENT
                b_prompt = f"{t['p_body']}\nTEXT: {txt_in}"
                b_content = clean_text(get_ai(b_prompt))
                
                # --- WORD GENERATION ---
                doc = Document()
                section = doc.sections[0]
                section.top_margin = Cm(1.0)
                section.left_margin = Cm(1.8)
                section.right_margin = Cm(1.8)
                
                # BANNER COLOR (Blu Professionale più chiaro)
                BANNER_COLOR = "2c5f85" # O "1F4E79"

                # Creazione Tabella Banner
                if proc_img:
                    tbl = doc.add_table(rows=1, cols=2)
                    tbl.columns[0].width = Cm(4.5)
                    tbl.columns[1].width = Cm(14)
                    c_img, c_txt = tbl.cell(0,0), tbl.cell(0,1)
                    set_cell_bg(c_img, BANNER_COLOR)
                    set_cell_bg(c_txt, BANNER_COLOR)
                    
                    # Foto
                    p = c_img.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    ib = io.BytesIO()
                    proc_img.save(ib, format='JPEG')
                    run.add_picture(ib, width=Cm(3.8)) # Foto leggermente più grande
                else:
                    tbl = doc.add_table(rows=1, cols=1)
                    c_txt = tbl.cell(0,0)
                    set_cell_bg(c_txt, BANNER_COLOR)

                # Parsing Dati
                parts = h_data.split('|')
                name = parts[0].strip() if len(parts)>0 else "Name Surname"
                # Separiamo indirizzo da email/tel
                address = parts[1].strip() if len(parts)>1 else ""
                contacts = " • ".join([x.strip() for x in parts[2:]]) # Tel e Email

                # Formattazione Testo Banner
                c_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                
                # Nome
                p1 = c_txt.paragraphs[0]
                if not proc_img: p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r1 = p1.add_run(name)
                r1.font.size = Pt(26)
                r1.font.color.rgb = RGBColor(255,255,255)
                r1.bold = True
                
                # Indirizzo (Nuova riga)
                p2 = c_txt.add_paragraph()
                if not proc_img: p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p2.paragraph_format.space_before = Pt(2)
                r2 = p2.add_run(address)
                r2.font.size = Pt(11)
                r2.font.color.rgb = RGBColor(240,240,240)
                
                # Contatti (Nuova riga)
                p3 = c_txt.add_paragraph()
                if not proc_img: p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r3 = p3.add_run(contacts)
                r3.font.size = Pt(11)
                r3.font.color.rgb = RGBColor(240,240,240)
                r3.bold = True

                # Spazio sotto
                doc.add_paragraph().space_after = Pt(10)
                
                # Titolo documento
                # h1 = doc.add_heading(t['cv_title'], 0)
                # h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Body Loop
                for line in b_content.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    # Rileva Titoli (Corti, Maiuscoli, Lettere presenti)
                    if len(line)<60 and line.isupper() and any(c.isalpha() for c in line) and "@" not in line:
                        p = doc.add_paragraph()
                        p.space_before = Pt(14)
                        p.space_after = Pt(4)
                        add_bottom_border(p)
                        run = p.add_run(line)
                        run.bold = True
                        run.font.size = Pt(13)
                        run.font.color.rgb = RGBColor(44, 95, 133) # Blu coordinato col banner
                    else:
                        p = doc.add_paragraph(line)
                        p.runs[0].font.size = Pt(11)
                        p.runs[0].font.name = 'Calibri'

                # Save
                bio = io.BytesIO()
                doc.save(bio)
                st.balloons()
                st.success(f"✅ {t['done']}")
                st.download_button(t["dl_btn"], bio.getvalue(), f"CV_{lang}.docx")

        except Exception as e:
            st.error(f"Error: {e}")
