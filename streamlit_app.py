import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gemini Model Debugger", page_icon="🐞")

st.title("🐞 Gemini Model Debugger")
st.markdown("Questo tool interroga l'API di Google per elencare i modelli disponibili per la tua chiave.")

# 1. Recupero API Key (Secrets o Manuale)
api_key = None

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ Chiave API trovata nei Secrets.")
except (FileNotFoundError, KeyError):
    st.warning("⚠️ Chiave API non trovata nei Secrets.")
    api_key = st.text_input("Inserisci la tua API Key manualmente:", type="password")

# 2. Logica di Verifica
if st.button("CERCA MODELLI DISPONIBILI"):
    if not api_key:
        st.error("❌ Errore: Nessuna API Key fornita.")
        st.stop()

    try:
        # Configurazione
        genai.configure(api_key=api_key)
        
        st.info("Tentativo di connessione a Google AI...")
        
        # 3. Listing dei Modelli
        models_iterator = genai.list_models()
        
        found_models = []
        for m in models_iterator:
            if 'generateContent' in m.supported_generation_methods:
                found_models.append(m)

        # 4. Output
        if found_models:
            st.success(f"✅ Connessione riuscita! Trovati {len(found_models)} modelli abilitati alla generazione di testo:")
            
            for m in found_models:
                with st.expander(f"🔹 {m.name}"):
                    st.code(f"Nome: {m.name}\nDisplay Name: {m.display_name}\nDescrizione: {m.description}")
        else:
            st.warning("⚠️ Connessione riuscita, ma non sono stati trovati modelli con metodo 'generateContent'. Controlla i permessi della chiave.")

    except Exception as e:
        st.error(f"❌ Errore durante la chiamata API:\n{e}")
