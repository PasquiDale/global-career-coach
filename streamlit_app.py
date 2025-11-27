import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Diagnostica Gemini", page_icon="🔍")

st.title("🔍 Test Diagnostico: Che modelli vede la tua chiave?")
st.info("Questo test interroga direttamente i server di Google per vedere quali porte sono aperte.")

# 1. Inserimento Chiave
api_key = st.text_input("Incolla qui la tua API Key (Proviamo prima quella GRATUITA di AI Studio)", type="password")

if st.button("LANCIA IL TEST 🚀"):
    if not api_key:
        st.warning("Inserisci prima la chiave!")
        st.stop()
    
    # 2. Configurazione
    try:
        genai.configure(api_key=api_key)
        st.write("✅ Connessione avviata...")
        
        # 3. Interrogazione (La parte magica)
        available_models = []
        all_models = genai.list_models()
        
        st.write("---")
        st.write("### 📡 Risposta dai Server di Google:")
        
        found_any = False
        for m in all_models:
            # Cerchiamo solo i modelli che generano testo (non quelli per le immagini o embedding)
            if 'generateContent' in m.supported_generation_methods:
                found_any = True
                st.success(f"🟢 TROVATO: `{m.name}`")
                st.caption(f"Descrizione: {m.description}")
                available_models.append(m.name)
        
        if not found_any:
            st.error("❌ Nessun modello trovato. La connessione funziona ma la chiave non ha accesso ai modelli di generazione testo.")
        else:
            st.balloons()
            st.success(f"Test Superato! La tua chiave può usare {len(available_models)} modelli.")
            
    except Exception as e:
        st.error("❌ ERRORE DI CONNESSIONE GRAVE:")
        st.code(str(e))
        st.write("Possibili cause: Chiave errata, Account Google bloccato, o limitazioni geografiche (VPN?).")
