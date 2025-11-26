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
    api_key = st.sidebar.text_input("Inserisci API Key", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"Errore Key: {e}")

# --- FUNZIONE CHIAMATA AI (GEMINI FLASH - IL PIÙ SICURO) ---
def get_gemini_response(prompt):
    try:
        # Usiamo FLASH: È veloce, stabile e non da errore 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"ERRORE TECNICO: {str(e)}"

def get_gemini_search(query, ctx):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        tools = [{'google_search': {}}]
        response = model.generate_content(f"{ctx} Query: {query}", tools=tools)
        return response.text
    except Exception as e:
        return f"ERRORE RICERCA: {str(e)}"

# --- TRADUZIONI ---
translations = {
    "Italiano": {
        "nav_title": "Navigazione", 
        "menu_home": "🏠 Home", "menu_cv": "📄 Riformatta CV",
        "menu_photo": "📸 Studio Foto", "menu_letter": "✍️ Lettera",
        "menu_match": "⚖️ Matching CV", "menu_search": "🌍 Ricerca Lavoro",
        "menu_sim": "🎙️ Simulazione", "menu_qa": "💡 Q&A Esperto",
        "welcome": "Benvenuto in Global Career Coach 🚀",
        "subtitle": "La piattaforma AI professionale per la tua carriera.",
        "card_cv": "Design professionale CV", "card_match": "Ottimizzazione ATS",
        "card_search": "Ricerca Globale", "card_sim": "Training Colloqui",
        "up_cv": "Carica CV (PDF)", "btn_gen": "Genera Documento",
        "proc": "Elaborazione in corso...", "ok": "Fatto!", "dl_word": "Scarica Word",
        "up_foto": "Carica Foto", "border": "Bordo", "dl_foto": "Scarica Foto",
        "job_ad": "Testo Annuncio", "btn_match": "Analizza", 
        "role": "Ruolo", "city": "Città", "btn_search": "Cerca",
        "start_sim": "Inizia", "you": "Tu", "q_label": "Domanda", "btn_ans": "Rispondi",
        "no_key": "Inserisci API Key.", "search_ctx": "Trova 5 offerte di lavoro reali con link."
    },
    "English": {
        "nav_title": "Navigation", 
        "menu_home": "🏠 Home", "menu_cv": "📄 Reformat CV",
        "menu_photo": "📸 Photo Studio", "menu_letter": "✍️ Cover Letter",
        "menu_match": "⚖️ Job Matching", "menu_search": "🌍 Job Search",
        "menu_sim": "🎙️ Interview Sim", "menu_qa": "💡 Expert Q&A",
        "welcome": "Welcome to Global Career Coach 🚀",
        "subtitle": "Professional AI career platform.",
        "card_cv": "Professional CV Design", "card_match": "ATS Optimization",
        "card_search": "Global Job Hunt", "card_sim": "Interview Training",
        "up_cv": "Upload CV (PDF)", "btn_gen": "Generate",
        "proc": "Processing...", "ok": "Done!", "dl_word": "Download Word",
        "up_foto": "Upload Photo", "border": "Border", "dl_foto": "Download Photo",
        "job_ad": "Job Ad", "btn_match": "Analyze", 
        "role": "Role", "city": "City", "btn_search": "Search",
        "start_sim": "Start", "you": "You", "q_label": "Question", "btn_ans": "Answer",
        "no_key": "Enter API Key.", "search_ctx": "Find 5 real job offers with links."
    },
     "Deutsch": {
        "nav_title": "Navigation", 
        "menu_home": "🏠 Startseite", "menu_cv": "📄 Lebenslauf",
        "menu_photo": "📸 Fotostudio", "menu_letter": "✍️ Anschreiben",
        "menu_match": "⚖️ Matching", "menu_search": "🌍 Jobsuche",
        "menu_sim": "🎙️ Interview", "menu_qa": "💡 Experten",
        "welcome": "Willkommen bei Global Career Coach 🚀",
        "subtitle": "Ihre professionelle Karriere-Plattform.",
        "card_cv": "CV Design", "card_match": "ATS Optimierung",
        "card_search": "Globale Suche", "card_sim": "Interview Training",
        "up_cv": "CV hochladen (PDF)", "btn_gen": "Erstellen",
        "proc": "Verarbeitung...", "ok": "Fertig!", "dl_word": "Word laden",
        "up_foto": "Foto hochladen", "border": "Rand", "dl_foto": "Foto laden",
        "job_ad": "Stellenanzeige", "btn_match": "Analysieren", 
        "role": "Position", "city": "Stadt", "btn_search": "Suchen",
        "start_sim": "Starten", "you": "Sie", "q_label": "Frage", "btn_ans": "Antworten",
        "no_key": "API Key eingeben.", "search_ctx": "Finde 5 echte Stellenangebote mit Links."
    },
    "Español": {
        "nav_title": "Navegación", "menu_home": "🏠 Inicio", "menu_cv": "📄 CV",
        "menu_photo": "📸 Foto", "menu_letter": "✍️ Carta",
        "menu_match": "⚖️ Matching", "menu_search": "🌍 Buscar",
        "menu_sim": "🎙️ Entrevista", "menu_qa": "💡 Expertos",
        "welcome": "Bienvenido a Global Career Coach 🚀",
        "subtitle": "Tu plataforma de carrera.",
        "card_cv": "Diseño CV", "card_match": "Optimización ATS",
        "card_search": "Búsqueda Global", "card_sim": "Entrenamiento",
        "up_cv": "Subir CV (PDF)", "btn_gen": "Generar",
        "proc": "Procesando...", "ok": "¡Hecho!", "dl_word": "Descargar Word",
        "up_foto": "Subir Foto", "border": "Borde", "dl_foto": "Descargar Foto",
        "job_ad": "Oferta", "btn_match": "Analizar", 
        "role": "Puesto", "city": "Ciudad", "btn_search": "Buscar",
        "start_sim": "Empezar", "you": "Tú", "q_label": "Pregunta", "btn_ans": "Responder",
        "no_key": "Introduce API Key.", "search_ctx": "Encuentra 5 ofertas reales con enlaces."
    },
    "Português": {
        "nav_title": "Navegação", "menu_home": "🏠 Início", "menu_cv": "📄 CV",
        "menu_photo": "📸 Foto", "menu_letter": "✍️ Carta",
        "menu_match": "⚖️ Matching", "menu_search": "🌍 Busca",
        "menu_sim": "🎙️ Entrevista", "menu_qa": "💡 Especialistas",
        "welcome": "Bem-vindo ao Global Career Coach 🚀",
        "subtitle": "Sua plataforma de carreira.",
        "card_cv": "Design CV", "card_match": "Otimização ATS",
        "card_search": "Busca Global", "card_sim": "Treinamento",
        "up_cv": "Enviar CV (PDF)", "btn_gen": "Gerar",
        "proc": "Processando...", "ok": "Pronto!", "dl_word": "Baixar Word",
        "up_foto": "Enviar Foto", "border": "Borda", "dl_foto": "Baixar Foto",
        "job_ad": "Anúncio", "btn_match": "Analisar", 
        "role": "Cargo", "city": "Cidade", "btn_search": "Buscar",
        "start_sim": "Iniciar", "you": "Você", "q_label": "Pergunta", "btn_ans": "Responder",
        "no_key": "Insira API Key.", "search_ctx": "Encontre 5 vagas reais com links."
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
    st.title(t["welcome"])
    st.subheader(t["subtitle"])
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**{t['menu_cv']}**\n\n{t['card_cv']}")
        st.info(f"**{t['menu_match']}**\n\n{t['card_match']}")
    with col2:
        st.info(f"**{t['menu_search']}**\n\n{t['card_search']}")
        st.info(f"**{t['menu_sim']}**\n\n{t['card_sim']}")

elif page == t["menu_cv"]:
    st.header(t["menu_cv"])
    if not api_key: st.warning(t["no_key"]); st.stop()
    f = st.file_uploader(t["up_cv"], type=["pdf"])
    if f and st.button(t["btn_gen"]):
        reader = pypdf.PdfReader(f)
        txt = "".join([p.extract_text() for p in reader.pages])
        with st.spinner(t["proc"]):
            # Chiamata al modello
            res = get_gemini_response(f"Rewrite CV professionally in {lang_code}. Plain text only:\n{txt}")
            
            # Se la risposta contiene "ERRORE", mostrala in rosso e ferma tutto
            if "ERRORE" in res:
                st.error(res)
            else:
                doc = Document()
                doc.add_heading('CURRICULUM VITAE', 0)
                for line in res.split('\n'):
                    if line.strip(): doc.add_paragraph(line)
                bio = io.BytesIO()
                doc.save(bio)
                st.success(t["ok"])
                st.download_button(t["dl_word"], bio.getvalue(), "CV_Pro.docx")

elif page == t["menu_photo"]:
    st.header(t["menu_photo"])
    img = st.file_uploader(t["up_foto"], type=["jpg","png"])
    if img:
        b = st.slider(t["border"], 0, 50, 15)
        i = Image.open(img)
        new_i = ImageOps.expand(i, border=b, fill='white')
        st.image(new_i, width=300)
        buf = io.BytesIO()
        new_i.save(buf, format="JPEG")
        st.download_button(t["dl_foto"], buf.getvalue(), "photo.jpg", "image/jpeg")

elif page == t["menu_letter"]:
    st.header(t["menu_letter"])
    if not api_key: st.warning(t["no_key"]); st.stop()
    ad = st.text_area(t["job_ad"])
    if ad and st.button(t["btn_gen"]):
        with st.spinner(t["proc"]):
            res = get_gemini_response(f"Write cover letter in {lang_code}:\n{ad}")
            if "ERRORE" in res: st.error(res)
            else: st.markdown(res)

elif page == t["menu_match"]:
    st.header(t["menu_match"])
    if not api_key: st.warning(t["no_key"]); st.stop()
    c = st.file_uploader(t["up_cv"], type=["pdf"], key="m")
    ad = st.text_area(t["job_ad"], key="ma")
    if c and ad and st.button(t["btn_match"]):
        reader = pypdf.PdfReader(c)
        txt = "".join([p.extract_text() for p in reader.pages])
        with st.spinner(t["proc"]):
            res = get_gemini_response(f"Match CV vs Job in {lang_code}. Score 0-100 & Feedback.\nCV:{txt}\nJOB:{ad}")
            if "ERRORE" in res: st.error(res)
            else: st.markdown(res)

elif page == t["menu_search"]:
    st.header(t["menu_search"])
    if not api_key: st.warning(t["no_key"]); st.stop()
    r = st.text_input(t["role"])
    l = st.text_input(t["city"])
    if r and l and st.button(t["btn_search"]):
        with st.spinner(t["proc"]):
            res = get_gemini_search(f"Jobs {r} in {l}", t["search_ctx"])
            if "ERRORE" in res: st.error(res)
            else: st.markdown(res)

elif page == t["menu_sim"]:
    st.header(t["menu_sim"])
    if not api_key: st.warning(t["no_key"]); st.stop()
    if "chat" not in st.session_state: st.session_state.chat = []
    if st.button(t["start_sim"]):
        st.session_state.chat = []
        q = get_gemini_response(f"Start interview in {lang_code}. Ask first question.")
        st.session_state.chat.append({"role":"assistant", "content":q})
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
    if u := st.chat_input(t["you"]):
        st.session_state.chat.append({"role":"user", "content":u})
        st.chat_message("user").write(u)
        with st.spinner("..."):
            hist = str(st.session_state.chat)
            ans = get_gemini_response(f"Interview {lang_code}. History: {hist}. User just answered. Give feedback & next question.")
            st.session_state.chat.append({"role":"assistant", "content":ans})
            st.chat_message("assistant").write(ans)

elif page == t["menu_qa"]:
    st.header(t["menu_qa"])
    if not api_key: st.warning(t["no_key"]); st.stop()
    q = st.text_input(t["q_label"])
    if q and st.button(t["btn_ans"]):
        res = get_gemini_response(f"Best answer for interview: {q} in {lang_code}")
        if "ERRORE" in res: st.error(res)
        else: st.markdown(res)
