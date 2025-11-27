import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
from PIL import Image, ImageOps
import pypdf

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="🚀",
    layout="wide"
)

# --- CSS PER NASCONDERE MENU E FOOTER ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: LINGUA E LOGIN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2910/2910756.png", width=50)
    st.title("Career Coach Pro")
    lang = st.selectbox("Lingua / Language", ["Italiano", "English", "Deutsch", "Español", "Português"])
    
    st.divider()
    st.markdown("### 🔐 Accesso Enterprise")
    # Inserimento manuale della chiave a pagamento
    api_key = st.text_input("Inserisci Chiave Google Cloud", type="password")

    if not api_key:
        st.warning("⬅️ Inserisci la chiave per sbloccare il sistema.")
        st.stop()

    # Configurazione AI
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Errore Chiave: {e}")

# --- MOTORE AI: GEMINI 2.5 PRO (Dalla tua lista verde) ---
def get_ai(prompt):
    try:
        # Usiamo il modello 2.5 PRO: Potente, Stabile e Disponibile per te
        model = genai.GenerativeModel('gemini-2.5-pro')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"ERRORE TECNICO: {str(e)}"

# --- TRADUZIONI ---
t = {
    "Italiano": {
        "nav": ["🏠 Home", "📄 CV", "📸 Foto", "✍️ Lettera", "🌍 Ricerca", "🎙️ Colloquio"],
        "wel": "Benvenuto in Career Coach Enterprise 🚀",
        "sub": "Powered by Gemini 2.5 Pro",
        "cv_tit": "Riformattazione Professionale CV",
        "up": "Carica il tuo CV (PDF)",
        "gen": "Genera Documento Word",
        "dl": "Scarica CV Ottimizzato",
        "photo_tit": "Studio Fotografico AI",
        "p_up": "Carica Foto Profilo",
        "bord": "Spessore Bordo",
        "job_tit": "Lettera di Presentazione",
        "job_txt": "Incolla qui l'annuncio di lavoro",
        "job_gen": "Scrivi Lettera",
        "search_tit": "Ricerca Lavoro Globale",
        "role": "Ruolo", "city": "Città", "find": "Trova Offerte",
        "sim_tit": "Simulatore Colloquio", "start": "Inizia", "ans": "Rispondi"
    },
    "English": {
        "nav": ["🏠 Home", "📄 CV", "📸 Photo", "✍️ Cover Letter", "🌍 Jobs", "🎙️ Interview"],
        "wel": "Welcome to Career Coach Enterprise 🚀",
        "sub": "Powered by Gemini 2.5 Pro",
        "cv_tit": "Professional CV Reformatting",
        "up": "Upload CV (PDF)",
        "gen": "Generate Word Doc",
        "dl": "Download Optimized CV",
        "photo_tit": "AI Photo Studio",
        "p_up": "Upload Profile Photo",
        "bord": "Border Size",
        "job_tit": "Cover Letter Generator",
        "job_txt": "Paste Job Description here",
        "job_gen": "Write Letter",
        "search_tit": "Global Job Search",
        "role": "Role", "city": "City", "find": "Find Jobs",
        "sim_tit": "Interview Simulator", "start": "Start", "ans": "Answer"
    }
}
# Fallback lingua inglese se non definita
txt = t.get(lang, t["English"])

# --- NAVIGAZIONE ---
page = st.sidebar.radio("Menu", txt["nav"])

# --- 1. HOME ---
if page == txt["nav"][0]:
    st.title(txt["wel"])
    st.subheader(txt["sub"])
    st.info("Sistema connesso ai server Google Enterprise. Quota illimitata attiva.")

# --- 2. CV ---
elif page == txt["nav"][1]:
    st.header(txt["cv_tit"])
    uploaded_file = st.file_uploader(txt["up"], type=["pdf"])
    
    if uploaded_file and st.button(txt["gen"]):
        try:
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for p in reader.pages: text += p.extract_text()
            
            with st.spinner("Gemini 2.5 Pro sta analizzando il tuo profilo..."):
                prompt = f"Sei un esperto HR globale. Riscrivi questo CV in {lang}. Usa un linguaggio 'Action-Oriented', migliora la grammatica e rendilo professionale. Mantieni i dati reali:\n{text}"
                res = get_ai(prompt)
                
                if "ERRORE" in res:
                    st.error(res)
                else:
                    doc = Document()
                    doc.add_heading('Curriculum Vitae', 0)
                    for line in res.split('\n'):
                        if line.strip(): 
                            if len(line) < 40 and line.isupper():
                                doc.add_heading(line, level=1)
                            else:
                                doc.add_paragraph(line)
                    bio = io.BytesIO()
                    doc.save(bio)
                    
                    st.success("Analisi completata!")
                    st.download_button(txt["dl"], bio.getvalue(), "CV_Pro.docx")
        except Exception as e:
            st.error(f"Errore: {e}")

# --- 3. FOTO ---
elif page == txt["nav"][2]:
    st.header(txt["photo_tit"])
    img = st.file_uploader(txt["p_up"], type=["jpg", "png"])
    if img:
        b = st.slider(txt["bord"], 0, 50, 15)
        i = Image.open(img)
        ni = ImageOps.expand(i, border=b, fill='white')
        st.image(ni, width=300)
        buf = io.BytesIO()
        ni.save(buf, format="JPEG")
        st.download_button("Download JPG", buf.getvalue(), "photo.jpg", "image/jpeg")

# --- 4. LETTERA ---
elif page == txt["nav"][3]:
    st.header(txt["job_tit"])
    ad = st.text_area(txt["job_txt"], height=200)
    if ad and st.button(txt["job_gen"]):
        with st.spinner("Scrittura in corso..."):
            res = get_ai(f"Scrivi una lettera di presentazione professionale in {lang} per questo annuncio:\n{ad}")
            st.markdown(res)

# --- 5. RICERCA (Simulata con AI per ora) ---
elif page == txt["nav"][4]:
    st.header(txt["search_tit"])
    c1, c2 = st.columns(2)
    r = c1.text_input(txt["role"])
    c = c2.text_input(txt["city"])
    if r and c and st.button(txt["find"]):
        with st.spinner("Analisi del mercato..."):
            # Gemini 2.5 è bravissimo a simulare headhunting
            res = get_ai(f"Agisci come un Headhunter in {lang}. Elenca 5 aziende reali a {c} che assumono spesso per il ruolo di {r}. Per ogni azienda spiega perché è una buona scelta.")
            st.markdown(res)

# --- 6. COLLOQUIO ---
elif page == txt["nav"][5]:
    st.header(txt["sim_tit"])
    if "chat" not in st.session_state: st.session_state.chat = []
    
    if st.button(txt["start"]):
        st.session_state.chat = []
        q = get_ai(f"Inizia un colloquio di lavoro in {lang}. Fai la prima domanda.")
        st.session_state.chat.append({"role":"assistant", "content":q})
        
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
    
    if u := st.chat_input(txt["ans"]):
        st.session_state.chat.append({"role":"user", "content":u})
        st.chat_message("user").write(u)
        with st.spinner("..."):
            # Manteniamo la memoria della chat
            hist = str(st.session_state.chat)
            ans = get_ai(f"Simulazione colloquio in {lang}. Storia: {hist}. L'utente ha appena risposto. Dai un breve feedback e fai la prossima domanda.")
            st.session_state.chat.append({"role":"assistant", "content":ans})
            st.chat_message("assistant").write(ans)
