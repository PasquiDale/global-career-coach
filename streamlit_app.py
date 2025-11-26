import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
from PIL import Image, ImageOps
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Global Career Coach",
    page_icon="suitcase",
    layout="wide"
)

# --- NASCONDI FOOTER E MENU STREAMLIT (White Label) ---
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
        st.error(f"Errore configurazione API: {e}")

# --- DIZIONARIO LINGUE ---
translations = {
    "Italiano": {
        "nav_title": "Navigazione",
        "menu_home": "🏠 Home",
        "menu_cv": "📄 Riformatta CV",
        "menu_photo": "📸 Studio Foto",
        "menu_letter": "✍️ Lettera Presentazione",
        "menu_match": "⚖️ Analisi Compatibilità",
        "menu_search": "🌍 Ricerca Lavoro",
        "menu_sim": "🎙️ Simulazione Colloquio",
        "menu_qa": "💡 Risposte Esperte",
        "welcome_title": "Benvenuto in Global Career Coach 🚀",
        "welcome_text": "La piattaforma professionale per portare la tua carriera al livello successivo.",
        "upload_cv": "Carica il tuo CV (PDF)",
        "download_word": "Scarica CV in Word",
        "photo_instruction": "Carica la tua foto profilo",
        "border_size": "Spessore bordo bianco",
        "download_photo": "Scarica Nuova Foto",
        "job_desc_label": "Incolla qui l'annuncio di lavoro",
        "generate_btn": "Genera Documento",
        "analyze_btn": "Analizza Compatibilità",
        "search_label": "Ruolo desiderato",
        "location_label": "Città / Regione",
        "search_btn": "Trova Offerte",
        "sim_start": "Inizia Simulazione",
        "sim_question": "Domanda del Recruiter:",
        "your_answer": "La tua risposta:",
        "feedback": "Feedback del Coach:",
        "next_q": "Prossima Domanda",
        "qa_label": "Inserisci una domanda difficile (es. 'Qual è il tuo difetto?')",
        "qa_btn": "Genera Risposta Migliore",
        "missing_key": "⚠️ Per iniziare, inserisci il Codice di Accesso o contatta l'amministratore.",
        "processing": "Elaborazione in corso...",
        "success": "Completato con successo!",
        "search_context": "Sei un esperto recruiter. Trova 5 offerte di lavoro REALI e ATTIVE per questo ruolo in questa città. Restituisci una lista con Titolo, Azienda e Link."
    },
    "English": {
        "nav_title": "Navigation",
        "menu_home": "🏠 Home",
        "menu_cv": "📄 Reformat CV",
        "menu_photo": "📸 Photo Studio",
        "menu_letter": "✍️ Cover Letter",
        "menu_match": "⚖️ Job Matching",
        "menu_search": "🌍 Job Search",
        "menu_sim": "🎙️ Interview Simulator",
        "menu_qa": "💡 Expert Answers",
        "welcome_title": "Welcome to Global Career Coach 🚀",
        "welcome_text": "The professional platform to take your career to the next level.",
        "upload_cv": "Upload your CV (PDF)",
        "download_word": "Download Word CV",
        "photo_instruction": "Upload your profile photo",
        "border_size": "White border thickness",
        "download_photo": "Download New Photo",
        "job_desc_label": "Paste the job description here",
        "generate_btn": "Generate Document",
        "analyze_btn": "Analyze Compatibility",
        "search_label": "Desired Role",
        "location_label": "City / Region",
        "search_btn": "Find Jobs",
        "sim_start": "Start Simulation",
        "sim_question": "Recruiter's Question:",
        "your_answer": "Your Answer:",
        "feedback": "Coach Feedback:",
        "next_q": "Next Question",
        "qa_label": "Enter a difficult question (e.g., 'What is your weakness?')",
        "qa_btn": "Get Best Answer",
        "missing_key": "⚠️ Please enter Access Code to start.",
        "processing": "Processing...",
        "success": "Completed successfully!",
        "search_context": "You are an expert recruiter. Find 5 REAL and ACTIVE job listings for this role in this city. Return a list with Title, Company, and Link."
    },
    "Deutsch": {
        "nav_title": "Navigation",
        "menu_home": "🏠 Startseite",
        "menu_cv": "📄 Lebenslauf Optimieren",
        "menu_photo": "📸 Fotostudio",
        "menu_letter": "✍️ Anschreiben",
        "menu_match": "⚖️ Job-Matching",
        "menu_search": "🌍 Jobsuche",
        "menu_sim": "🎙️ Interview-Simulator",
        "menu_qa": "💡 Experten-Antworten",
        "welcome_title": "Willkommen beim Global Career Coach 🚀",
        "welcome_text": "Die professionelle Plattform für Ihre Karriere.",
        "upload_cv": "Laden Sie Ihren Lebenslauf hoch (PDF)",
        "download_word": "Word-Lebenslauf herunterladen",
        "photo_instruction": "Profilbild hochladen",
        "border_size": "Dicke des weißen Randes",
        "download_photo": "Neues Foto herunterladen",
        "job_desc_label": "Stellenanzeige hier einfügen",
        "generate_btn": "Dokument erstellen",
        "analyze_btn": "Kompatibilität prüfen",
        "search_label": "Gewünschte Position",
        "location_label": "Stadt / Region",
        "search_btn": "Jobs finden",
        "sim_start": "Simulation starten",
        "sim_question": "Frage des Recruiters:",
        "your_answer": "Ihre Antwort:",
        "feedback": "Coach Feedback:",
        "next_q": "Nächste Frage",
        "qa_label": "Schwierige Frage eingeben (z.B. 'Was ist Ihre Schwäche?')",
        "qa_btn": "Beste Antwort generieren",
        "missing_key": "⚠️ Bitte Zugangscode eingeben.",
        "processing": "Verarbeitung...",
        "success": "Erfolgreich abgeschlossen!",
        "search_context": "Du bist ein erfahrener Recruiter. Finde 5 ECHTE und AKTUELLE Stellenangebote für diese Position in dieser Stadt. Liste Titel, Unternehmen und Link auf."
    },
    "Español": {
        "nav_title": "Navegación",
        "menu_home": "🏠 Inicio",
        "menu_cv": "📄 Reformatear CV",
        "menu_photo": "📸 Estudio Fotográfico",
        "menu_letter": "✍️ Carta de Presentación",
        "menu_match": "⚖️ Análisis de Compatibilidad",
        "menu_search": "🌍 Buscar Empleo",
        "menu_sim": "🎙️ Simulador de Entrevista",
        "menu_qa": "💡 Respuestas Expertas",
        "welcome_title": "Bienvenido a Global Career Coach 🚀",
        "welcome_text": "La plataforma profesional para impulsar tu carrera.",
        "upload_cv": "Sube tu CV (PDF)",
        "download_word": "Descargar CV en Word",
        "photo_instruction": "Sube tu foto de perfil",
        "border_size": "Grosor del borde blanco",
        "download_photo": "Descargar Nueva Foto",
        "job_desc_label": "Pega aquí la oferta de trabajo",
        "generate_btn": "Generar Documento",
        "analyze_btn": "Analizar Compatibilidad",
        "search_label": "Puesto deseado",
        "location_label": "Ciudad / Región",
        "search_btn": "Buscar Ofertas",
        "sim_start": "Iniciar Simulación",
        "sim_question": "Pregunta del reclutador:",
        "your_answer": "Tu respuesta:",
        "feedback": "Feedback del Coach:",
        "next_q": "Siguiente Pregunta",
        "qa_label": "Introduce una pregunta difícil",
        "qa_btn": "Generar Mejor Respuesta",
        "missing_key": "⚠️ Por favor ingresa el Código de Acceso.",
        "processing": "Procesando...",
        "success": "¡Completado con éxito!",
        "search_context": "Eres un reclutador experto. Encuentra 5 ofertas de trabajo REALES y ACTIVAS para este puesto en esta ciudad. Devuelve una lista con Título, Empresa y Enlace."
    },
    "Português": {
        "nav_title": "Navegação",
        "menu_home": "🏠 Início",
        "menu_cv": "📄 Reformatar CV",
        "menu_photo": "📸 Estúdio de Foto",
        "menu_letter": "✍️ Carta de Apresentação",
        "menu_match": "⚖️ Análise de Compatibilidade",
        "menu_search": "🌍 Busca de Emprego",
        "menu_sim": "🎙️ Simulador de Entrevista",
        "menu_qa": "💡 Respostas Especializadas",
        "welcome_title": "Bem-vindo ao Global Career Coach 🚀",
        "welcome_text": "A plataforma profissional para impulsionar sua carreira.",
        "upload_cv": "Envie seu CV (PDF)",
        "download_word": "Baixar CV em Word",
        "photo_instruction": "Envie sua foto de perfil",
        "border_size": "Espessura da borda branca",
        "download_photo": "Baixar Nova Foto",
        "job_desc_label": "Cole o anúncio de emprego aqui",
        "generate_btn": "Gerar Documento",
        "analyze_btn": "Analisar Compatibilidade",
        "search_label": "Cargo desejado",
        "location_label": "Cidade / Região",
        "search_btn": "Buscar Vagas",
        "sim_start": "Iniciar Simulação",
        "sim_question": "Pergunta do Recrutador:",
        "your_answer": "Sua resposta:",
        "feedback": "Feedback do Coach:",
        "next_q": "Próxima Pergunta",
        "qa_label": "Insira uma pergunta difícil",
        "qa_btn": "Gerar Melhor Resposta",
        "missing_key": "⚠️ Por favor, insira o Código de Acesso.",
        "processing": "Processando...",
        "success": "Concluído com sucesso!",
        "search_context": "Você é um recrutador experiente. Encontre 5 vagas de emprego REAIS e ATIVAS para este cargo nesta cidade. Retorne uma lista com Título, Empresa e Link."
    }
}

# --- SIDEBAR ---
with st.sidebar:
    lang_code = st.selectbox("🌐 Language / Lingua", ["Italiano", "English", "Deutsch", "Español", "Português"])
    t = translations[lang_code]
    st.divider()
    st.header(t["nav_title"])
    page = st.radio("Go to", [
        t["menu_home"], t["menu_cv"], t["menu_photo"], 
        t["menu_letter"], t["menu_match"], t["menu_search"], 
        t["menu_sim"], t["menu_qa"]
    ], label_visibility="collapsed")

# --- FUNZIONI UTILI (CORRETTE) ---
def get_gemini_response(prompt):
    # QUI ERA L'ERRORE: Ho messo 'gemini-1.5-pro' che è stabile
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)
    return response.text

def get_gemini_search(query, language_ctx):
    # ANCHE QUI CORRETTO
    model = genai.GenerativeModel('gemini-1.5-pro')
    tools = [{'google_search': {}}]
    final_prompt = f"{language_ctx} Query: {query}"
    response = model.generate_content(final_prompt, tools=tools)
    return response.text

# --- PAGINE ---

# 1. HOME
if page == t["menu_home"]:
    st.title(t["welcome_title"])
    st.write(t["welcome_text"])
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**{t['menu_cv']}**\n\nProfessional redesign.")
        st.info(f"**{t['menu_match']}**\n\nATS Optimization.")
    with col2:
        st.info(f"**{t['menu_search']}**\n\nGlobal Job Hunt.")
        st.info(f"**{t['menu_sim']}**\n\nInterview Training.")

# 2. RIFORMATTA CV
elif page == t["menu_cv"]:
    st.header(t["menu_cv"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    
    uploaded_file = st.file_uploader(t["upload_cv"], type=["pdf"])
    if uploaded_file:
        import pypdf
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page_num in range(len(reader.pages)):
            text += reader.pages[page_num].extract_text()
            
        if st.button(t["generate_btn"]):
            with st.spinner(t["processing"]):
                prompt = f"Act as a professional CV Writer. Rewrite this CV in {lang_code} language. Make it action-oriented, professional and clean. \n\nCV TEXT:\n{text}"
                improved_text = get_gemini_response(prompt)
                
                doc = Document()
                style = doc.styles['Normal']
                font = style.font
                font.name = 'Calibri'
                font.size = Pt(11)
                
                doc.add_heading('CURRICULUM VITAE', 0)
                
                for line in improved_text.split('\n'):
                    if line.strip():
                        if line.isupper() or len(line) < 40 and ":" not in line:
                            p = doc.add_heading(line, level=1)
                        else:
                            p = doc.add_paragraph(line)
                
                bio = io.BytesIO()
                doc.save(bio)
                
                st.success(t["success"])
                st.download_button(
                    label=t["download_word"],
                    data=bio.getvalue(),
                    file_name="CV_Professional.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

# 3. FOTO STUDIO
elif page == t["menu_photo"]:
    st.header(t["menu_photo"])
    uploaded_img = st.file_uploader(t["photo_instruction"], type=["jpg", "png", "jpeg"])
    
    if uploaded_img:
        border = st.slider(t["border_size"], 0, 50, 15)
        image = Image.open(uploaded_img)
        img_with_border = ImageOps.expand(image, border=border, fill='white')
        st.image(img_with_border, caption="Preview", use_column_width=False, width=300)
        
        buf = io.BytesIO()
        img_with_border.save(buf, format="JPEG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label=t["download_photo"],
            data=byte_im,
            file_name="photo_pro.jpg",
            mime="image/jpeg"
        )

# 4. LETTERA PRESENTAZIONE
elif page == t["menu_letter"]:
    st.header(t["menu_letter"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    
    job_ad = st.text_area(t["job_desc_label"], height=200)
    if st.button(t["generate_btn"]) and job_ad:
        with st.spinner(t["processing"]):
            prompt = f"Write a professional cover letter in {lang_code} for this job ad. Tone: Professional, enthusiastic, persuasive.\n\nJOB AD:\n{job_ad}"
            letter = get_gemini_response(prompt)
            st.markdown(letter)
            st.download_button("Download .txt", letter, "Cover_Letter.txt")

# 5. MATCH CV
elif page == t["menu_match"]:
    st.header(t["menu_match"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    
    col_cv, col_ad = st.columns(2)
    with col_cv:
        cv_file = st.file_uploader(t["upload_cv"], type=["pdf"], key="match_cv")
    with col_ad:
        ad_text = st.text_area(t["job_desc_label"], height=150, key="match_ad")
        
    if st.button(t["analyze_btn"]) and cv_file and ad_text:
        import pypdf
        reader = pypdf.PdfReader(cv_file)
        cv_text = ""
        for page_num in range(len(reader.pages)):
            cv_text += reader.pages[page_num].extract_text()
            
        with st.spinner(t["processing"]):
            prompt = f"Analyze the match between this CV and Job Ad in {lang_code}. Give a score 0-100. List 3 strengths and 3 missing keywords. Suggest changes.\n\nCV:{cv_text}\n\nAD:{ad_text}"
            analysis = get_gemini_response(prompt)
            st.markdown(analysis)

# 6. RICERCA LAVORO
elif page == t["menu_search"]:
    st.header(t["menu_search"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    
    col1, col2 = st.columns(2)
    role = col1.text_input(t["search_label"])
    loc = col2.text_input(t["location_label"])
    
    if st.button(t["search_btn"]) and role and loc:
        with st.spinner(t["processing"]):
            query = f"Job offers for {role} in {loc}"
            results = get_gemini_search(query, t["search_context"])
            st.markdown(results)

# 7. SIMULAZIONE COLLOQUIO
elif page == t["menu_sim"]:
    st.header(t["menu_sim"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if st.button(t["sim_start"]):
        st.session_state.messages = []
        start_prompt = f"Act as a strict Recruiter. Start a job interview in {lang_code}. Ask the first question."
        first_q = get_gemini_response(start_prompt)
        st.session_state.messages.append({"role": "assistant", "content": first_q})
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if user_input := st.chat_input(t["your_answer"]):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.spinner("Thinking..."):
            hist = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            prompt = f"Continue the interview in {lang_code}. History:\n{hist}\n\nUser just answered. Give brief feedback and ask next question."
            response = get_gemini_response(prompt)
            
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# 8. Q&A DIFFICILI
elif page == t["menu_qa"]:
    st.header(t["menu_qa"])
    if not api_key: st.warning(t["missing_key"]); st.stop()
    
    q = st.text_input(t["qa_label"])
    if st.button(t["qa_btn"]) and q:
        with st.spinner(t["processing"]):
            prompt = f"Provide the perfect professional answer to this interview question in {lang_code}: '{q}'. Explain why it works."
            ans = get_gemini_response(prompt)
            st.markdown(ans)
