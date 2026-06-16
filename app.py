import streamlit as st
import os
import time
from datetime import date
from google import genai
from google.genai import types

# Configurazione grafica
st.set_page_config(page_title="PATBOT - Assistente Normativa", page_icon="🤖")
st.title("🤖 PATBOT - Assistente Normativa")
st.subheader("Procedura 'APAPI - Terzo Figlio'")

# 1. Recupero chiave
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Configurazione incompleta: Chiave API non trovata!")
    st.stop()

# Inizializzazione Client
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

client = st.session_state.client
PERCORSO_CARTELLA = "normativa"

# 2. Caricamento documenti (Corretto per la libreria genai)
@st.cache_resource(show_spinner=False)
def carica_documenti_nel_cloud():
    file_pdf = [os.path.join(PERCORSO_CARTELLA, f) for f in os.listdir(PERCORSO_CARTELLA) if f.lower().endswith('.pdf')]
    docs_caricati = []
    
    for percorso in file_pdf:
        doc = client.files.upload(file=percorso)
        while doc.state.name == "PROCESSING":
            time.sleep(1)
            doc = client.files.get(name=doc.name)
        docs_caricati.append(doc)
    return docs_caricati

try:
    documenti = carica_documenti_nel_cloud()
except Exception as e:
    st.error(f"⚠️ Errore caricamento PDF: {e}")
    st.stop()

# 3. Chat Engine (Corretto per la libreria genai)
if "chat_engine" not in st.session_state:
    system_inst = "Sei PATBOT, assistente esperto della Provincia di Trento per la procedura 'APAPI - Terzo Figlio'..."
    
    # Creiamo la lista degli input corretta: File + Prompt di sistema
    input_iniziale = documenti + ["Questi sono i documenti normativi. Rispondi basandoti solo su di essi."]
    
    st.session_state.chat_engine = client.chats.create(
        model="gemini-1.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=system_inst,
            temperature=0.0
        )
    )
    # Invio iniziale separato per stabilire il contesto
    st.session_state.chat_engine.send_message(input_iniziale)

# 4. Interfaccia Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["ruolo"]):
        st.write(msg["testo"])

if domanda := st.chat_input("Scrivi la tua domanda..."):
    st.session_state.messages.append({"ruolo": "user", "testo": domanda})
    with st.chat_message("user"):
        st.write(domanda)
        
    with st.chat_message("assistant"):
        try:
            risposta = st.session_state.chat_engine.send_message(domanda)
            st.write(risposta.text)
            st.session_state.messages.append({"ruolo": "assistant", "testo": risposta.text})
        except Exception as e:
            st.error(f"⚠️ Errore di esecuzione: {e}")
