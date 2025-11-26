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
