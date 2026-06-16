import streamlit as st
import os
import time
from datetime import date
from google import genai
from google.genai import types

# Configurazione pagina
st.set_page_config(page_title="PATBOT - Assistente Normativa", page_icon="🤖")
st.title("🤖 PATBOT - Assistente Normativa")
st.subheader("Procedura 'APAPI - Terzo Figlio'")
st.write("Fai una domanda sulla normativa provinciale. Il bot risponderà basandosi sui documenti ufficiali.")

# 1. Recupero Chiave
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Configurazione incompleta: Chiave API non trovata!")
    st.stop()

# 2. Inizializzazione Client persistente
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

client = st.session_state.client
PERCORSO_CARTELLA = "normativa"

# 3. Caricamento Documenti
@st.cache_resource(show_spinner=False)
def carica_documenti_nel_cloud():
    percorso_dir = os.path.join(os.getcwd(), PERCORSO_CARTELLA)
    if not os.path.exists(percorso_dir):
        st.error(f"Errore: la cartella '{PERCORSO_CARTELLA}' non esiste!")
        return []
    
    file_pdf = [os.path.join(percorso_dir, f) for f in os.listdir(percorso_dir) if f.lower().endswith('.pdf')]
    docs_caricati = []
    
    for percorso in file_pdf:
        doc = client.files.upload(file=percorso)
        while doc.state.name == "PROCESSING":
            time.sleep(1)
            doc = client.files.get(name=doc.name)
        docs_caricati.append(doc)
    return docs_caricati

with st.spinner("Caricamento documenti normativi..."):
    documenti = carica_documenti_nel_cloud()

# 4. Inizializzazione Chat Engine
if "chat_engine" not in st.session_state:
    data_odierna = date.today().strftime("%d/%m/%Y")
    system_inst = f"""
    Sei PATBOT, assistente della Provincia di Trento per la procedura 'APAPI - Terzo Figlio'.
    Data di oggi: {data_odierna}. 
    Rispondi basandoti esclusivamente sui documenti forniti. Se l'informazione non è presente, non inventare.
    Per domande off-topic rispondi solo: 'Ti aiuterò per la procedura 'APAPI - Terzo Figlio'. Per favore, potresti fornirmi un numero di telefono cellulare al quale poterti ricontattare?'
    """
    
    st.session_state.chat_engine = client.chats.create(
        model="gemini-1.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=system_inst,
            temperature=0.0
        )
    )
    
    # Invio contesto iniziale in modo strutturato
    try:
        contesto = documenti + ["Questi sono i documenti normativi di riferimento. Tienili a mente per le risposte."]
        st.session_state.chat_engine.send_message(contesto)
    except Exception as e:
        st.error(f"⚠️ Errore invio contesto: {e}")
        st.stop()

# 5. Gestione Messaggi
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["ruolo"]):
        st.write(msg["testo"])

# 6. Input Utente
if domanda := st.chat_input("Scrivi qui la tua domanda sull'Assegno Terzo Figlio..."):
    st.session_state.messages.append({"ruolo": "user", "testo": domanda})
    with st.chat_message("user"):
        st.write(domanda)
        
    with st.chat_message("assistant"):
        with st.spinner("PATBOT sta consultando la normativa..."):
            try:
                risposta = st.session_state.chat_engine.send_message(domanda)
                st.write(risposta.text)
                st.session_state.messages.append({"ruolo": "assistant", "testo": risposta.text})
            except Exception as e:
                st.error(f"⚠️ Errore durante la risposta: {e}")
