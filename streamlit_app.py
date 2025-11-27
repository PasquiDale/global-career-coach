import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Career Coach Pro", page_icon="🚀", layout="wide")

# --- CSS ---
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

# --- LOGIN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=60)
    st.title("Career Coach")
    lang = st.selectbox("Lingua / Language", ["Deutsch", "Italiano", "English", "Español", "Português"])
    st.divider()
    api_key = st.text_input("Inserisci API Key", type="password")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except: pass

# --- FUNZIONE AI (GEMINI 3 PRO) ---
def get_ai(prompt):
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE: {str(e)}"

# --- FUNZIONI GRAFICHE WORD ---
def set_cell_bg(cell, color_hex):
    """Colora lo sfondo della cella"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_bottom_border(paragraph):
    """Linea sotto i titoli"""
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

# --- TRADUZIONI ---
trans = {
    "Deutsch": {"up_pdf":"PDF Lebenslauf", "up_img":"Foto (Optional)", "gen":"CV Generieren", "dl":"Download Word", "load":"Design wird erstellt..."},
    "Italiano": {"up_pdf":"Carica CV (PDF)", "up_img":"Carica Foto (Opzionale)", "gen":"Genera CV Completo", "dl":"Scarica Word", "load":"Creazione CV e Design..."},
    "English": {"up_pdf":"Upload CV (PDF)", "up_img":"Upload Photo (Optional)", "gen":"Generate CV", "dl":"Download Word", "load":"Creating Design..."},
}
t = trans.get(lang, trans["English"])

# --- MAIN ---
st.title("Global Career Coach 🚀")
st.subheader("CV Builder All-in-One")

if not api_key:
    st.warning("⬅️ Chiave API mancante.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    f_pdf = st.file_uploader(t["up_pdf"], type=["pdf"])
with col2:
    f_img = st.file_uploader(t["up_img"], type=["jpg", "png", "jpeg"])

if f_pdf and st.button(t["gen"]):
    try:
        # 1. LETTURA PDF
        reader = pypdf.PdfReader(f_pdf)
        txt_pdf = ""
        for p in reader.pages: txt_pdf += p.extract_text()
        
        with st.spinner(t["load"]):
            # 2. AI: ESTRAZIONE DATI PER BANNER
            prompt_header = f"""
            Estrai dal testo SOLO: Nome Cognome | Indirizzo | Telefono | Email.
            Formatta ESATTAMENTE così: Nome Cognome | Indirizzo | Telefono | Email
            Se manca qualcosa non scriverlo.
            TESTO: {txt_pdf[:1500]}
            """
            header_data = get_ai(prompt_header).strip()
            
            # 3. AI: RISCRITTURA CORPO
            prompt_body = f"""
            Sei un esperto HR. Riscrivi il corpo del CV in {lang}.
            NON includere l'intestazione (Nome, Contatti) perché la metto nel banner.
            Usa titoli MAIUSCOLI per le sezioni.
            Sii professionale e action-oriented.
            TESTO: {txt_pdf}
            """
            body_content = clean_text(get_ai(prompt_body))

            # --- CREAZIONE DOCUMENTO ---
            doc = Document()
            
            # Margini
            section = doc.sections[0]
            section.top_margin = Cm(1.27)
            section.left_margin = Cm(1.5)
            section.right_margin = Cm(1.5)

            # === BANNER BLU (TABELLA) ===
            # Se c'è la foto facciamo 2 colonne, altrimenti 1
            if f_img:
                table = doc.add_table(rows=1, cols=2)
                # Larghezza colonne (Foto piccola, Testo largo)
                table.columns[0].width = Cm(4.5) 
                table.columns[1].width = Cm(14)
                
                cell_img = table.cell(0, 0)
                cell_txt = table.cell(0, 1)
                
                # Sfondo Blu per entrambe
                set_cell_bg(cell_img, "0E2F44")
                set_cell_bg(cell_txt, "0E2F44")
                
                # --- GESTIONE FOTO ---
                # Aggiungiamo bordo bianco con PIL prima di inserire
                image_pil = Image.open(f_img)
                # Bordo bianco 3% della larghezza
                border_size = int(min(image_pil.size) * 0.03) 
                image_with_border = ImageOps.expand(image_pil, border=border_size, fill='white')
                
                # Salvataggio temporaneo per Word
                img_byte_arr = io.BytesIO()
                image_with_border.save(img_byte_arr, format='JPEG')
                
                # Inserimento in cella sinistra
                p_img = cell_img.paragraphs[0]
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                # Calcolo Aspect Ratio per altezza fissa (es. 3.5 cm)
                run_img = p_img.add_run()
                run_img.add_picture(img_byte_arr, width=Cm(3.5)) 
                
            else:
                # Solo testo (1 colonna)
                table = doc.add_table(rows=1, cols=1)
                cell_txt = table.cell(0, 0)
                set_cell_bg(cell_txt, "0E2F44")

            # --- GESTIONE TESTO BANNER ---
            cell_txt.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            
            parts = header_data.split('|')
            name = parts[0].strip() if len(parts) > 0 else "Nome Cognome"
            contacts = "  •  ".join([p.strip() for p in parts[1:]])
            
            # Nome
            p_name = cell_txt.paragraphs[0]
            if not f_img: p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_name = p_name.add_run(name)
            run_name.font.size = Pt(24)
            run_name.font.color.rgb = RGBColor(255, 255, 255)
            run_name.bold = True
            
            # Contatti
            p_cont = cell_txt.add_paragraph(contacts)
            if not f_img: p_cont.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_cont = p_cont.runs[0]
            run_cont.font.size = Pt(10)
            run_cont.font.color.rgb = RGBColor(230, 230, 230)

            # Spazio sotto il banner
            doc.add_paragraph().space_after = Pt(12)

            # === CORPO DEL CV ===
            for line in body_content.split('\n'):
                line = line.strip()
                if not line: continue
                
                if len(line) < 60 and line.isupper() and any(c.isalpha() for c in line):
                    # Titolo Sezione
                    p = doc.add_paragraph()
                    p.space_before = Pt(12)
                    add_bottom_border(p)
                    run = p.add_run(line)
                    run.bold = True
                    run.font.size = Pt(12)
                    run.font.color.rgb = RGBColor(14, 47, 68)
                else:
                    # Testo Normale
                    p = doc.add_paragraph(line)
                    p.paragraph_format.space_after = Pt(2)
                    run = p.runs[0]
                    run.font.size = Pt(10.5)
                    run.font.name = 'Calibri'

            # Download
            bio = io.BytesIO()
            doc.save(bio)
            st.success(t["done"])
            st.download_button(t["dl"], bio.getvalue(), "CV_Professional.docx")

    except Exception as e:
        st.error(f"Errore tecnico: {e}")
