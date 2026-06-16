import streamlit as st
import os
import time
from google import genai
from google.genai import types

# 1. Configurazione
st.set_page_config(page_title="PATBOT", page_icon="🤖")
st.title("🤖 PATBOT - Assistente Normativa")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configura la GEMINI_API_KEY nei Secrets di Streamlit!")
    st.stop()

# 2. Inizializzazione Client
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

client = st.session_state.client

# 3. Caricamento File (Gestione errori migliorata)
@st.cache_resource(show_spinner=False)
def carica_files():
    cartella = "normativa"
    file_pdf = [os.path.join(cartella, f) for f in os.listdir(cartella) if f.lower().endswith('.pdf')]
    docs = []
    for percorso in file_pdf:
        doc = client.files.upload(file=percorso)
        while doc.state.name == "PROCESSING":
            time.sleep(2)
            doc = client.files.get(name=doc.name)
        docs.append(doc)
    return docs

try:
    documenti = carica_files()
except Exception as e:
    st.error(f"Errore caricamento file: {e}")
    st.stop()

# 4. Chat Engine (Sintassi standard pulita)
if "chat" not in st.session_state:
    # Creiamo la chat direttamente con il modello corretto
    st.session_state.chat = client.chats.create(
        model="gemini-1.5-pro",
        config=types.GenerateContentConfig(
            system_instruction="Sei PATBOT, esperto della procedura 'APAPI - Terzo Figlio'. Rispondi basandoti solo sui file forniti."
        )
    )
    # Inviamo i documenti come primo messaggio di contesto
    st.session_state.chat.send_message(documenti + ["Questi sono i documenti di riferimento."])

# 5. Interfaccia
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Chiedi a PATBOT..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            # Invio domanda
            risposta = st.session_state.chat.send_message(prompt)
            st.write(risposta.text)
            st.session_state.messages.append({"role": "assistant", "content": risposta.text})
        except Exception as e:
            st.error(f"Errore: {e}")
