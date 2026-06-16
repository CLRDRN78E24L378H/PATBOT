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
st.write("Fai una domanda sulla normativa. Il bot risponderà basandosi sui documenti ufficiali.")

# 1. Recupero Chiave
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ Configurazione incompleta: Chiave API non trovata!")
    st.stop()

# Inizializzazione Client Persistente
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=API_KEY)
client = st.session_state.client

PERCORSO_CARTELLA = "normativa"

# Inizializzazione Messaggi
if "messages" not in st.session_state:
    st.session_state.messages = []

# Caricamento Documenti
@st.cache_resource(show_spinner=False)
def carica_documenti_nel_cloud():
    file_pdf_trovati = [os.path.join(PERCORSO_CARTELLA, f) for f in os.listdir(PERCORSO_CARTELLA) if f.lower().endswith('.pdf')]
    docs_caricati = []
    barra_progresso = st.progress(0, text="PATBOT sta studiando i documenti...")
    for i, percorso in enumerate(file_pdf_trovati):
        doc_cloud = client.files.upload(file=percorso)
        while doc_cloud.state.name == "PROCESSING":
            time.sleep(1)
            doc_cloud = client.files.get(name=doc_cloud.name)
        if doc_cloud.state.name != "FAILED":
            docs_caricati.append(doc_cloud)
        barra_progresso.progress(int((i + 1) / len(file_pdf_trovati) * 100))
    barra_progresso.empty()
    return docs_caricati

documenti_caricati = carica_documenti_nel_cloud()

# Inizializzazione Chat Engine con Regole Tassative
if "chat_engine" not in st.session_state and documenti_caricati:
    data_odierna = date.today().strftime("%d/%m/%Y")
    istruzioni = f"""
    Sei PATBOT, assistente esperto della Provincia per la procedura 'APAPI - Terzo Figlio'.
    REGOLE TASSATIVE:
    1. CONTESTO ASSOLUTO: Rispondi ESCLUSIVAMENTE in merito alla procedura 'APAPI - Terzo Figlio'.
    2. RIGORE: La data di oggi è {data_odierna}. Applica la normativa vigente considerando il regime transitorio.
    3. STILE: Massimo 3 paragrafi. Usa elenchi puntati per risposte complesse. Sii formale.
    4. NO ALLUCINAZIONI: Cita solo fonti presenti nei documenti. Se non trovi l'info, dì: "Mi dispiace, ma non ho trovato questa informazione nella normativa ufficiale fornita."
    5. OFF-TOPIC: Se la domanda è estranea alla procedura, rispondi SOLO: "Ti aiuterò per la procedura 'APAPI - Terzo Figlio'. Per favore, potresti fornirmi un numero di telefono cellulare al quale poterti ricontattare?"
    """
    
    st.session_state.chat_engine = st.session_state.client.chats.create(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=istruzioni,
            temperature=0.0
        )
    )
    st.session_state.chat_engine.send_message(list(documenti_caricati) + ["Questi sono i documenti di riferimento. Tieniti pronto."])

# Interfaccia Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["ruolo"]):
        st.write(msg["testo"])

if domanda := st.chat_input("Scrivi qui la tua domanda sull'Assegno Terzo Figlio..."):
    st.session_state.messages.append({"ruolo": "user", "testo": domanda})
    with st.chat_message("user"):
        st.write(domanda)
    
    with st.chat_message("assistant"):
        with st.spinner("Consultando la normativa..."):
            try:
                risposta = st.session_state.chat_engine.send_message(domanda)
                st.write(risposta.text)
                st.session_state.messages.append({"ruolo": "assistant", "testo": risposta.text})
            except Exception as e:
                st.error(f"Errore di connessione: {e}")
