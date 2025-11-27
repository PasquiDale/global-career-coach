import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Test Chiave a Pagamento", page_icon="💰")

st.title("💰 Test Diagnostico: Chiave Enterprise")
st.info("Inserisci la tua chiave a pagamento (Google Cloud) per vedere quali modelli sono abilitati.")

api_key = st.text_input("Incolla Chiave Google Cloud", type="password")

if st.button("VERIFICA"):
    if not api_key:
        st.stop()
    
    try:
        genai.configure(api_key=api_key)
        st.write("Connessione in corso...")
        
        all_models = genai.list_models()
        
        found = False
        for m in all_models:
            if 'generateContent' in m.supported_generation_methods:
                found = True
                st.success(f"✅ DISPONIBILE: `{m.name}`")
        
        if not found:
            st.error("❌ Nessun modello trovato. La chiave è valida ma non ha i permessi API Generative Language attivi su Google Cloud.")
            
    except Exception as e:
        st.error(f"❌ ERRORE: {e}")
