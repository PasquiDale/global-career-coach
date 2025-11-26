import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor
from PIL import Image, ImageOps
import io
import pypdf

# -----------------------------------------------------------------------------
# CONFIGURAZIONE PAGINA E STILI
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CareerPro AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato per nascondere menu default e migliorare l'estetica
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    h1 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FUNZIONI DI UTILITÀ (BACKEND)
# -----------------------------------------------------------------------------

def get_gemini_response(input_text, prompt, api_key):
    """Chiama l'API di Gemini."""
    if not api_key:
        st.error("Inserisci la tua Gemini API Key nella sidebar per continuare.")
        return None
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([input_text, prompt])
        return response.text
    except Exception as e:
        st.error(f"Errore API Gemini: {str(e)}")
        return None

def extract_text_from_pdf(uploaded_file):
    """Estrae testo da un PDF caricato."""
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return str(e)

def create_word_docx(text_content):
    """Genera un file Word formattato dal testo ottimizzato."""
    doc = Document()
    
    # Stile Titolo
    heading = doc.add_heading('Curriculum Vitae', 0)
    heading.alignment = 1  # Center
    
    # Aggiungi il contenuto generato (parsing semplificato)
    # Gemini di solito restituisce testo strutturato con Markdown (**Title**)
    # Qui facciamo un parsing semplice per pulire il markdown base
    lines = text_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('**') and line.endswith('**'):
            # Titoli di sezione
            clean_line = line.replace('**', '').upper()
            p = doc.add_paragraph()
            run = p.add_run(clean_line)
            run.bold = True
            run.font.size = Pt(14)
            run.font.color.rgb = RGBColor(0, 51, 102) # Navy Blue
        elif line.startswith('* ') or line.startswith('- '):
            # Elenchi puntati
            clean_line = line[2:]
            doc.add_paragraph(clean_line, style='List Bullet')
        else:
            # Testo normale
            clean_line = line.replace('**', '') # Rimuovi bold residui
            doc.add_paragraph(clean_line)

    bio = io.BytesIO()
    doc.save(bio)
    return bio

def add_border_to_image(image, border_size):
    """Aggiunge un bordo bianco all'immagine."""
    return ImageOps.expand(image, border=int(border_size), fill='white')

# -----------------------------------------------------------------------------
# INTERFACCIA UTENTE (SIDEBAR)
# -----------------------------------------------------------------------------

with st.sidebar:
    st.title("🤖 CareerPro AI")
    st.markdown("Il tuo consulente di carriera intelligente.")
    
    api_key = st.text_input("Inserisci Gemini API Key", type="password")
    
    st.markdown("---")
    menu_options = [
        "🏠 Home",
        "📝 Riformatta CV",
        "🖼️ Foto Studio",
        "✍️ Generatore Lettera",
        "⚖️ Match CV & Offerta",
        "🔍 Ricerca Lavoro",
        "🗣️ Simulatore Colloquio",
        "💡 Q&A Difficili"
    ]
    selection = st.radio("Navigazione", menu_options)
    
    st.markdown("---")
    st.info("💡 Suggerimento: Per il simulatore, tieni il microfono spento e scrivi in chat!")

# -----------------------------------------------------------------------------
# PAGINE DELL'APPLICAZIONE
# -----------------------------------------------------------------------------

# 1. HOME
if selection == "🏠 Home":
    st.title("Benvenuto in CareerPro AI 🚀")
    st.markdown("""
    Sono il tuo assistente virtuale potenziato dall'Intelligenza Artificiale. 
    Ecco come posso aiutarti oggi:
    
    *   **📝 Riformatta CV:** Trasformo il tuo vecchio PDF in un documento Word moderno e incisivo.
    *   **🖼️ Foto Studio:** Aggiungo bordi professionali alla tua foto profilo.
    *   **⚖️ ATS Killer:** Analizzo il tuo CV rispetto a un annuncio per superare i filtri automatici.
    *   **🔍 Job Hunter:** Trovo le offerte reali e costruisco link di ricerca per te.
    *   **🗣️ Roleplay:** Simuliamo un colloquio reale in chat.
    
    👈 **Scegli una funzione dal menu a sinistra per iniziare!**
    """)

# 2. RIFORMATTA CV
elif selection == "📝 Riformatta CV":
    st.title("Riformattazione CV Professionale")
    st.markdown("Carica il tuo CV attuale. L'AI lo analizzerà, riscriverà i punti deboli e creerà un Word scaricabile.")
    
    uploaded_file = st.file_uploader("Carica il tuo CV (PDF o TXT)", type=["pdf", "txt"])
    
    if uploaded_file and st.button("Analizza e Riscrivi"):
        with st.spinner("L'AI sta lavorando sul tuo CV..."):
            # Estrazione testo
            if uploaded_file.type == "application/pdf":
                text = extract_text_from_pdf(uploaded_file)
            else:
                text = str(uploaded_file.read(), "utf-8")
            
            # Prompt per Gemini
            prompt = """
            Agisci come un Esperto HR Senior. Riscrivi il seguente contenuto del CV per renderlo professionale, 
            orientato ai risultati (Action-Oriented) e ben strutturato. 
            Migliora la grammatica e il lessico. 
            Struttura l'output in modo chiaro usando **TITOLI IN GRASSETTO** per le sezioni 
            (ESPERIENZA, ISTRUZIONE, SKILLS) e elenchi puntati.
            Non aggiungere commenti, restituisci solo il testo del CV pronto.
            """
            
            rewritten_text = get_gemini_response(text, prompt, api_key)
            
            if rewritten_text:
                st.success("CV Riscritto con successo!")
                
                # Anteprima
                with st.expander("Vedi anteprima testo"):
                    st.markdown(rewritten_text)
                
                # Generazione Word
                docx_file = create_word_docx(rewritten_text)
                
                st.download_button(
                    label="📥 Scarica CV in Word (.docx)",
                    data=docx_file.getvalue(),
                    file_name="CV_Ottimizzato_CareerPro.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

# 3. FOTO STUDIO
elif selection == "🖼️ Foto Studio":
    st.title("Studio Fotografico CV")
    st.markdown("Aggiungi un bordo bianco professionale per far risaltare la tua foto su sfondi colorati.")
    
    img_file = st.file_uploader("Carica la tua foto (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="Originale", width=200)
        
        border_size = st.slider("Spessore del bordo (pixel)", 0, 50, 15)
        
        if st.button("Applica Bordo"):
            new_img = add_border_to_image(image, border_size)
            st.image(new_img, caption="Risultato", width=250)
            
            # Prepare download
            buf = io.BytesIO()
            new_img.save(buf, format="JPEG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 Scarica Nuova Foto",
                data=byte_im,
                file_name="Foto_CV_Professional.jpg",
                mime="image/jpeg"
            )

# 4. GENERATORE LETTERA
elif selection == "✍️ Generatore Lettera":
    st.title("Generatore Lettera di Presentazione")
    
    job_desc = st.text_area("Incolla qui il testo dell'annuncio di lavoro", height=200)
    user_context = st.text_area("Brevi note su di te (es. 'Ho 5 anni di esperienza sales', 'Sono neolaureato')", height=100)
    
    if st.button("Genera Lettera") and job_desc:
        prompt = f"""
        Scrivi una lettera di presentazione formale e persuasiva in Italiano per questo annuncio di lavoro.
        Usa le informazioni dell'utente se presenti.
        La lettera deve evidenziare le soft skills e la motivazione.
        
        Note Utente: {user_context}
        """
        
        with st.spinner("Scrivendo la lettera..."):
            letter = get_gemini_response(job_desc, prompt, api_key)
            if letter:
                st.subheader("La tua Lettera")
                st.write(letter)
                st.download_button("Scarica testo (.txt)", letter, file_name="Lettera_Presentazione.txt")

# 5. MATCH CV & OFFERTA
elif selection == "⚖️ Match CV & Offerta":
    st.title("Analisi Compatibilità ATS")
    
    col1, col2 = st.columns(2)
    with col1:
        cv_upload = st.file_uploader("1. Carica il tuo CV", type=["pdf", "txt"])
    with col2:
        job_txt = st.text_area("2. Incolla l'annuncio", height=150)
        
    if st.button("Analizza Compatibilità") and cv_upload and job_txt:
        with st.spinner("Il Recruiter AI sta confrontando i dati..."):
            if cv_upload.type == "application/pdf":
                cv_text = extract_text_from_pdf(cv_upload)
            else:
                cv_text = str(cv_upload.read(), "utf-8")
                
            prompt = f"""
            Confronta il CV fornito con l'Annuncio di Lavoro.
            
            Fornisci l'output in questo formato esatto:
            **PERCENTUALE COMPATIBILITÀ:** [0-100]%
            
            **PUNTI DI FORZA:**
            - Punto 1
            - Punto 2
            - Punto 3
            
            **MANCANZE CRITICHE (Keywords mancanti):**
            - Mancanza 1
            - Mancanza 2
            
            **CONSIGLI ATS:**
            Suggerimenti concreti su cosa modificare nel CV.
            
            ANNUNCIO: {job_txt}
            """
            
            analysis = get_gemini_response(cv_text, prompt, api_key)
            if analysis:
                st.markdown(analysis)

# 6. RICERCA LAVORO
elif selection == "🔍 Ricerca Lavoro":
    st.title("Job Hunter Assistito")
    st.markdown("Genera link diretti alle migliori ricerche sui portali locali.")
    
    col1, col2 = st.columns(2)
    with col1:
        role = st.text_input("Che ruolo cerchi?", "Impiegato Commerciale")
    with col2:
        city = st.text_input("Dove?", "Zurigo")
        
    if st.button("Cerca Offerte"):
        st.subheader(f"🌐 Link Attivi per {role} a {city}")
        
        # Costruzione URL Dinamici (Funziona senza API Search a pagamento)
        linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={role}&location={city}"
        indeed_url = f"https://ch.indeed.com/jobs?q={role}&l={city}"
        jobsch_url = f"https://www.jobs.ch/de/stellenangebote/?location={city}&term={role}"
        google_jobs_url = f"https://www.google.com/search?q=lavoro+{role}+{city}&ibp=htl;jobs"
        
        st.markdown(f"""
        Ecco dove trovare le offerte migliori aggiornate ad oggi:
        
        *   🚀 **LinkedIn:** [Clicca qui per vedere le offerte]({linkedin_url})
        *   💼 **Indeed Svizzera:** [Clicca qui per vedere le offerte]({indeed_url})
        *   🇨🇭 **Jobs.ch:** [Clicca qui per vedere le offerte]({jobsch_url})
        *   🔍 **Google Jobs:** [Clicca qui per vedere le offerte]({google_jobs_url})
        """)
        
        # Chiediamo a Gemini consigli sulle aziende in quella zona
        if api_key:
            with st.expander("Consigli AI sulle aziende in zona"):
                prompt = f"Elenca 5 aziende importanti a {city} che spesso assumono per il ruolo di {role}. Solo nomi e breve descrizione."
                companies = get_gemini_response("", prompt, api_key)
                st.write(companies)

# 7. SIMULATORE COLLOQUIO
elif selection == "🗣️ Simulatore Colloquio":
    st.title("Simulatore di Colloquio AI")
    
    # Inizializzazione session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "interview_active" not in st.session_state:
        st.session_state.interview_active = False
    if "q_count" not in st.session_state:
        st.session_state.q_count = 0

    # Start button
    if not st.session_state.interview_active:
        if st.button("Inizia Colloquio"):
            st.session_state.interview_active = True
            st.session_state.messages = []
            st.session_state.q_count = 0
            
            initial_prompt = "Sei un Recruiter severo ma giusto. Inizia il colloquio presentandoti brevemente e facendo la prima domanda al candidato per un ruolo generico. Non fare lunghe premesse."
            intro = get_gemini_response("Start", initial_prompt, api_key)
            st.session_state.messages.append({"role": "assistant", "content": intro})
            st.rerun()

    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if prompt := st.chat_input("Scrivi la tua risposta..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate AI response
        if st.session_state.q_count < 5:
            st.session_state.q_count += 1
            ai_prompt = f"""
            Il candidato ha risposto: "{prompt}".
            
            1. Dai un breve feedback sulla risposta (Critico ma costruttivo).
            2. Fai la prossima domanda di colloquio.
            3. Se siamo alla domanda 5, concludi il colloquio e dai un voto finale da 1 a 10.
            
            Mantieni il ruolo di Recruiter.
            """
            
            with st.spinner("Il Recruiter sta valutando..."):
                response = get_gemini_response("", ai_prompt, api_key)
                
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
        else:
             st.info("Colloquio terminato. Ricarica la pagina per iniziarne uno nuovo.")

# 8. Q&A DIFFICILI
elif selection == "💡 Q&A Difficili":
    st.title("Generatore Risposte Perfette")
    
    question = st.text_input("Qual è la domanda che ti spaventa? (es. 'Qual è il tuo peggior difetto?')")
    
    if st.button("Genera Risposta") and question:
        prompt = f"""
        L'utente deve rispondere a questa domanda di colloquio: "{question}".
        
        Scrivi una risposta:
        1. Diplomatica e Professionale.
        2. Che trasformi un eventuale negativo in positivo.
        3. Pronta per essere recitata (in prima persona).
        """
        
        with st.spinner("Elaborazione strategia..."):
            answer = get_gemini_response(question, prompt, api_key)
            st.success("Ecco cosa dovresti dire:")
            st.markdown(f"> {answer}")

# Footer
st.markdown("---")
st.markdown("Developed with ❤️ by CareerPro AI - Powered by Streamlit & Gemini")
