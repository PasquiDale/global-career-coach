import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
import io
from PIL import Image, ImageOps

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="suitcase",
    layout="wide"
)

# --- NASCONDI FOOTER ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- GESTIONE API KEY ---
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("API Key (Access Code)", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Errore API Key: {e}")

# --- FUNZIONE INTELLIGENTE (TRY-CATCH) ---
def get_gemini_response(prompt):
    # Tenta 3 modelli diversi prima di arrendersi
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            continue # Se fallisce, prova il prossimo
            
    return "Errore: Impossibile contattare l'AI con questa chiave. Controlla i permessi o crea una nuova chiave gratuita su AI Studio."

def get_gemini_search(query, language_ctx):
    # La ricerca funziona meglio con i modelli Pro o Flash
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        tools = [{'google_search': {}}]
        final_prompt = f"{language_ctx} Query: {query}"
        response = model.generate_content(final_prompt, tools=tools)
        return response.text
    except:
        return "Errore nella ricerca. La tua chiave potrebbe non supportare Google Search Grounding."

# --- TRADUZIONI ---
translations = {
    "Italiano": {
        "nav_title": "Navigazione", "menu_home": "🏠 Home", "menu_cv": "📄 Riformatta CV",
        "menu_photo": "📸 Studio Foto", "menu_letter": "✍️ Lettera Presentazione",
        "menu_match": "⚖️ Analisi Compatibilità", "menu_search": "🌍 Ricerca Lavoro",
        "menu_sim": "🎙️ Simulazione Colloquio", "menu_qa": "💡 Risposte Esperte",
        "welcome_title": "Benvenuto in Global Career Coach 🚀",
        "welcome_text": "La piattaforma professionale per la tua carriera.",
        "upload_cv": "Carica CV (PDF)", "generate_btn": "Genera Documento",
        "processing": "Elaborazione...", "success": "Fatto!", "download_word": "Scarica Word",
        "photo_instruction": "Carica Foto", "border_size": "Bordo", "download_photo": "Scarica Foto",
        "job_desc_label": "Testo Annuncio", "analyze_btn": "Analizza", 
        "search_label": "Ruolo", "location_label": "Città", "search_btn": "Cerca",
        "sim_start": "Inizia", "your_answer": "Tua risposta", "qa_label": "Domanda difficile", "qa_btn": "Rispondi",
        "missing_key": "Inserisci API Key per iniziare.",
        "search_context": "Trova 5 offerte di lavoro reali con link."
    },
    "English": {
        "nav_title": "Navigation", "menu_home": "🏠 Home", "menu_cv": "📄 Reformat CV",
        "menu_photo": "📸 Photo Studio", "menu_letter": "✍️ Cover Letter",
        "menu_match": "⚖️ Job Matching", "menu_search": "🌍 Job Search",
        "menu_sim": "🎙️ Interview Sim", "menu_qa": "💡 Expert QA",
        "welcome_title": "Welcome to Global Career Coach 🚀",
        "welcome_text": "Professional career platform.",
        "upload_cv": "Upload CV (PDF)", "generate_btn": "Generate",
        "processing": "Processing...", "success": "Done!", "download_word": "Download Word",
        "photo_instruction": "Upload Photo", "border_size": "Border", "download_photo": "Download Photo",
        "job_desc_label": "Job Ad", "analyze_btn": "Analyze", 
        "search_label": "Role", "location_label": "City", "search_btn": "Search",
        "sim_start": "Start", "your_answer": "Your answer", "qa_label": "Hard question", "qa_btn": "Answer",
        "missing_key": "Enter API Key to start.",
        "search_context": "Find 5 real job offers with links."
    },
     "Deutsch": {
        "nav_title": "Navigation", "menu_home": "🏠 Startseite", "menu_cv": "📄 Lebenslauf",
        "menu_photo": "📸 Fotostudio", "menu_letter": "✍️ Anschreiben",
        "menu_match": "⚖️ Matching", "menu_search": "🌍 Jobsuche",
        "menu_sim": "🎙️ Interview", "menu_qa": "💡 Experten",
        "welcome_title": "Willkommen bei Global Career Coach 🚀",
        "welcome_text": "Ihre Karriere-Plattform.",
        "upload_cv": "CV hochladen (PDF)", "generate_btn": "Erstellen",
        "processing": "Verarbeitung...", "success": "Fertig!", "download_word": "Word laden",
        "photo_instruction": "Foto hochladen", "border_size": "Rand", "download_photo": "Foto laden",
        "job_desc_label": "Stellenanzeige", "analyze_btn": "Analysieren", 
        "search_label": "Position", "location_label": "Stadt", "search_btn": "Suchen",
        "sim_start": "Starten", "your_answer": "Ihre Antwort", "qa_label": "Frage", "qa_btn": "Antworten",
        "missing_key": "API Key eingeben.",
        "search_context": "Finde 5 echte Stellenangebote mit Links."
    },
    "Español": {
        "nav_title": "Navegación", "menu_home": "🏠 Inicio", "menu_cv": "📄 CV",
        "menu_photo": "📸 Foto", "menu_letter": "✍️ Carta",
        "menu_match": "⚖️ Matching", "menu_search": "🌍 Buscar",
        "menu_sim": "🎙️ Entrevista", "menu_qa": "💡 Expertos",
        "welcome_title": "Bienvenido a Global Career Coach 🚀",
        "welcome_text": "Tu plataforma de carrera.",
        "upload_cv": "Subir CV (PDF)", "generate_btn": "Generar",
        "processing": "Procesando...", "success": "¡Hecho!", "download_word": "Descargar Word",
        "photo_instruction": "Subir Foto", "border_size": "Borde", "download_photo": "Descargar Foto",
        "job_desc_label": "Oferta", "analyze_btn": "Analizar", 
        "search_label": "Puesto", "location_label": "Ciudad", "search_btn": "Buscar",
        "sim_start": "Empezar", "your_answer": "Tu respuesta", "qa_label": "Pregunta", "qa_btn": "Responder",
        "missing_key": "Introduce API Key.",
        "search_context": "Encuentra 5 ofertas reales con enlaces."
    },
    "Português": {
        "nav_title": "Navegação", "menu_home": "🏠 Início", "menu_cv": "📄 CV",
        "menu_photo": "📸 Foto", "menu_letter": "✍️ Carta",
        "menu_match": "⚖️ Matching", "menu_search": "🌍 Busca",
        "menu_sim": "🎙️ Entrevista", "menu_qa": "💡 Especialistas",
        "welcome_title": "Bem-vindo ao Global Career Coach 🚀",
        "welcome_text": "Sua plataforma de carreira.",
        "upload_cv": "Enviar CV (PDF)", "generate_btn": "Gerar",
        "processing": "Processando...", "success": "Pronto!", "download_word": "Baixar Word",
        "photo_instruction": "Enviar Foto", "border_size": "Borda", "download_photo": "Baixar Foto",
        "job_desc_label": "Anúncio", "analyze_btn": "Analisar", 
        "search_label": "Cargo", "location_label": "Cidade", "search_btn": "Buscar",
        "sim_start": "Iniciar", "your_answer": "Sua resposta", "qa_label": "Pergunta", "qa_btn": "Responder",
        "missing_key": "Insira API Key.",
        "search_context": "Encontre 5 vagas reais com links."
    }
}

# --- SIDEBAR ---
with st.sidebar:
    lang_code = st.selectbox("🌐 Language", ["Italiano", "English", "Deutsch", "Español", "Português"])
    t = translations[lang_code]
    st.divider()
    page = st.radio(t["nav_title"], [
        t["menu_home"], t["menu_cv"], t["menu_photo"], 
        t["menu_letter"], t["menu_match"], t["menu_search"], 
        t["menu_sim"], t["menu_qa"]
    ])

# --- MAIN ---
if page == t["menu_home"]:
    st.title(t["welcome_title"])
    st.write(t["welcome_text"])

elif page == t["menu_cv"]:
    st.header(t["menu_cv"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    f = st.file_uploader(t["upload_cv"], type=["pdf"])
    if f and st.button(t["generate_btn"]):
        import pypdf
        reader = pypdf.PdfReader(f)
        txt = "".join([p.extract_text() for p in reader.pages])
        with st.spinner(t["processing"]):
            res = get_gemini_response(f"Rewrite CV professionally in {lang_code}:\n{txt}")
            doc = Document()
            for line in res.split('\n'):
                if line.strip(): doc.add_paragraph(line)
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(t["download_word"], bio.getvalue(), "CV.docx")

elif page == t["menu_photo"]:
    st.header(t["menu_photo"])
    img = st.file_uploader(t["photo_instruction"], type=["jpg","png"])
    if img:
        b = st.slider(t["border_size"], 0, 50, 15)
        i = Image.open(img)
        new_i = ImageOps.expand(i, border=b, fill='white')
        st.image(new_i, width=300)
        buf = io.BytesIO()
        new_i.save(buf, format="JPEG")
        st.download_button(t["download_photo"], buf.getvalue(), "photo.jpg", "image/jpeg")

elif page == t["menu_letter"]:
    st.header(t["menu_letter"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    ad = st.text_area(t["job_desc_label"])
    if ad and st.button(t["generate_btn"]):
        with st.spinner(t["processing"]):
            res = get_gemini_response(f"Write cover letter in {lang_code}:\n{ad}")
            st.markdown(res)

elif page == t["menu_match"]:
    st.header(t["menu_match"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    c = st.file_uploader(t["upload_cv"], type=["pdf"], key="m")
    ad = st.text_area(t["job_desc_label"], key="ma")
    if c and ad and st.button(t["analyze_btn"]):
        import pypdf
        reader = pypdf.PdfReader(c)
        txt = "".join([p.extract_text() for p in reader.pages])
        with st.spinner(t["processing"]):
            res = get_gemini_response(f"Match CV vs Job in {lang_code}. Score 0-100 & Feedback.\nCV:{txt}\nJOB:{ad}")
            st.markdown(res)

elif page == t["menu_search"]:
    st.header(t["menu_search"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    r = st.text_input(t["search_label"])
    l = st.text_input(t["location_label"])
    if r and l and st.button(t["search_btn"]):
        with st.spinner(t["processing"]):
            res = get_gemini_search(f"Jobs {r} in {l}", t["search_context"])
            st.markdown(res)

elif page == t["menu_sim"]:
    st.header(t["menu_sim"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    if "chat" not in st.session_state: st.session_state.chat = []
    if st.button(t["sim_start"]):
        st.session_state.chat = []
        q = get_gemini_response(f"Start interview in {lang_code}. Ask first question.")
        st.session_state.chat.append({"role":"assistant", "content":q})
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
    if u := st.chat_input(t["your_answer"]):
        st.session_state.chat.append({"role":"user", "content":u})
        st.chat_message("user").write(u)
        with st.spinner("..."):
            hist = str(st.session_state.chat)
            ans = get_gemini_response(f"Interview {lang_code}. History: {hist}. User just answered. Give feedback & next question.")
            st.session_state.chat.append({"role":"assistant", "content":ans})
            st.chat_message("assistant").write(ans)

elif page == t["menu_qa"]:
    st.header(t["menu_qa"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    q = st.text_input(t["qa_label"])
    if q and st.button(t["qa_btn"]):
        st.markdown(get_gemini_response(f"Best answer for interview: {q} in {lang_code}"))
