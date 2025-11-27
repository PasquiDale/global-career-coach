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

# --- MEMORIA DI SESSIONE (Il "Cervello" che ricorda il CV) ---
if 'cv_text_memory' not in st.session_state:
    st.session_state.cv_text_memory = ""

# --- CSS ---
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

def clean_header_data(text):
    bad_words = ["Nome:", "Name:", "Indirizzo:", "Address:", "Email:", "Tel:", "**"]
    for word in bad_words: text = text.replace(word, "")
    return text.strip()

def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- TRADUZIONI ---
trans = {
    "Deutsch": {
        "menu_cv": "1. Lebenslauf & Foto", "menu_cl": "2. Anschreiben",
        "step1": "Foto", "step2": "Lebenslauf (PDF)", "gen": "CV Generieren", 
        "load": "Design wird erstellt...", "bord": "Rahmen", "dl_btn": "Word Herunterladen", 
        "txt_up": "PDF hier hochladen", "txt_img": "Foto hier hochladen",
        "job_tit": "Stellenanzeige", "job_ph": "Fügen Sie hier die Stellenbeschreibung ein...",
        "cl_gen": "Anschreiben Generieren", "cl_load": "Anschreiben wird geschrieben...",
        "cl_done": "Anschreiben fertig!", "cl_dl": "Anschreiben Herunterladen",
        "no_cv_warn": "⚠️ Bitte laden Sie zuerst Ihren Lebenslauf im Menü '1. Lebenslauf & Foto' hoch."
    },
    "Italiano": {
        "menu_cv": "1. CV & Foto", "menu_cl": "2. Lettera Presentazione",
        "step1": "Foto", "step2": "CV (PDF)", "gen": "Genera CV", 
        "load": "Creazione Design...", "bord": "Bordo", "dl_btn": "Scarica Word", 
        "txt_up": "Carica PDF qui", "txt_img": "Carica Foto qui",
        "job_tit": "Annuncio di Lavoro", "job_ph": "Incolla qui il testo dell'offerta di lavoro...",
        "cl_gen": "Scrivi Lettera", "cl_load": "Scrittura lettera strategica in corso...",
        "cl_done": "Lettera Pronta!", "cl_dl": "Scarica Lettera",
        "no_cv_warn": "⚠️ Per favore carica prima il tuo CV nel menu '1. CV & Foto'."
    },
    "English": {
        "menu_cv": "1. CV & Photo", "menu_cl": "2. Cover Letter",
        "step1": "Photo", "step2": "CV (PDF)", "gen": "Generate CV", 
        "load": "Creating Design...", "bord": "Border", "dl_btn": "Download Word", 
        "txt_up": "Upload PDF here", "txt_img": "Upload Photo here",
        "job_tit": "Job Description", "job_ph": "Paste the job ad here...",
        "cl_gen": "Write Letter", "cl_load": "Writing strategic letter...",
        "cl_done": "Letter Ready!", "cl_dl": "Download Letter",
        "no_cv_warn": "⚠️ Please upload your CV first in the '1. CV & Photo' menu."
    },
}
# Fallback
t = trans.get(lang, trans["English"]) 

# --- NAVIGAZIONE ---
page = st.sidebar.radio("Menu", [t["menu_cv"], t["menu_cl"]])

# ==========================================
# PAGINA 1: CV & FOTO (La tua preferita)
# ==========================================
if page == t["menu_cv"]:
    st.title("Global Career Coach 🚀")
    
    # FOTO
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"<div class='upload-label'>{t['step1']}</div>", unsafe_allow_html=True)
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
            st.markdown(f"""<div class="photo-preview"><img src="data:image/jpeg;base64,{b64_img}" width="150" style="border-radius:2px;"></div>""", unsafe_allow_html=True)

    st.divider()

    # PDF
    st.markdown(f"<div class='upload-label'>{t['step2']}</div>", unsafe_allow_html=True)
    f_pdf = st.file_uploader("Upload2", type=["pdf"], label_visibility="collapsed")

    if st.button(t["gen"], type="primary"):
        if not f_pdf:
            st.error("PDF Missing!")
        else:
            try:
                reader = pypdf.PdfReader(f_pdf)
                txt_in = ""
                for p in reader.pages: txt_in += p.extract_text()
                
                # SALVO IL TESTO IN MEMORIA PER DOPO!
                st.session_state.cv_text_memory = txt_in
                
                with st.spinner(t["load"]):
                    # 1. HEADER
                    h_prompt = f"Estrai: Nome Cognome | Indirizzo | Telefono | Email.\nTESTO: {txt_in[:2000]}"
                    h_data = clean_header_data(get_ai(h_prompt).strip())
                    
                    # 2. BODY
                    b_prompt = f"Sei HR Expert. Riscrivi CV in {lang}. NO Intro. NO Contatti. TITOLI MAIUSCOLI.\nTESTO: {txt_in}"
                    b_content = clean_text(get_ai(b_prompt))

                    # WORD
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
                        
                        c_img.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        p_img = c_img.paragraphs[0]
                        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_img.paragraph_format.space_before = Pt(10)
                        p_img.paragraph_format.space_after = Pt(10)
                        run = p_img.add_run()
                        ib = io.BytesIO()
                        proc_img.save(ib, format='JPEG')
                        run.add_picture(ib, width=Cm(3.8))
                    else:
                        tbl = doc.add_table(rows=1, cols=1)
                        c_txt = tbl.cell(0,0)
                        set_cell_bg(c_txt, BANNER_COLOR)

                    parts = h_data.split('|')
                    name = parts[0].strip() if len(parts)>0 else "Name"
                    addr = parts[1].strip() if len(parts)>1 else ""
                    tel = parts[2].strip() if len(parts)>2 else ""
                    email = parts[3].strip() if len(parts)>3 else ""
                    contact_line = f"{tel}  •  {email}"

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
                    st.success("✅ OK!")
                    st.download_button(t["dl_btn"], bio.getvalue(), f"CV_{lang}.docx")

            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# PAGINA 2: LETTERA DI PRESENTAZIONE
# ==========================================
elif page == t["menu_cl"]:
    st.header(t["menu_cl"])
    
    # Controllo se c'è un CV in memoria
    if not st.session_state.cv_text_memory:
        st.info(t["no_cv_warn"])
        # Opzione di caricamento manuale se l'utente salta il passaggio 1
        st.markdown("---")
        st.caption("Oppure carica un CV qui:")
        f_pdf_cl = st.file_uploader("Upload CV Manual", type=["pdf"], label_visibility="collapsed")
        if f_pdf_cl:
            reader = pypdf.PdfReader(f_pdf_cl)
            for p in reader.pages: st.session_state.cv_text_memory += p.extract_text()
            st.rerun() # Ricarica per nascondere l'uploader
    else:
        st.success("✅ CV caricato in memoria.")
        
        st.subheader(t["job_tit"])
        job_ad = st.text_area(t["job_ph"], height=200)
        
        if st.button(t["cl_gen"], type="primary"):
            if not job_ad:
                st.error("Inserisci il testo dell'annuncio!")
            else:
                with st.spinner(t["cl_load"]):
                    # PROMPT LETTERA
                    prompt_cl = f"""
                    Sei un esperto di carriera. Scrivi una Lettera di Presentazione in {lang}.
                    
                    INPUT:
                    1. IL MIO CV: {st.session_state.cv_text_memory}
                    2. L'ANNUNCIO DI LAVORO: {job_ad}
                    
                    ISTRUZIONI:
                    - Analizza le mie competenze nel CV e collegale ai requisiti dell'Annuncio.
                    - Usa un tono professionale, persuasivo ed entusiasta.
                    - Struttura standard: Intestazione, Saluto, Corpo (Perché io? Perché voi?), Conclusione.
                    - Non inventare dati.
                    """
                    
                    cl_content = get_ai(prompt_cl)
                    
                    st.markdown("### Anteprima:")
                    st.write(cl_content)
                    
                    # Download .txt (o Word semplice)
                    st.download_button(t["cl_dl"], cl_content, f"CoverLetter_{lang}.txt")
