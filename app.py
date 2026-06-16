import streamlit as st
import os
import time
from datetime import date
from google import genai
from google.genai import types

st.set_page_config(page_title="PATBOT - Assistente Normativa", page_icon="🤖")
st.title("🤖 PATBOT - Assistente Normativa")
st.subheader("Procedura 'APAPI - Terzo Figlio'")
st.write("Fai una domanda sulla normativa provinciale. Il bot risponderà basandosi sui documenti ufficiali.")

if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ Chiave API non trovata nella cassaforte (Secrets)!")
    st.stop()

# 1. SALVATAGGIO CLIENT IN MEMORIA (Antidoto per l'errore "Client closed")
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=API_KEY)

PERCORSO_CARTELLA = "normativa"

if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource(show_spinner=False)
def carica_documenti_nel_cloud():
    if not os.path.exists(PERCORSO_CARTELLA):
        return []
    
    file_pdf_trovati = [f for f in os.listdir(PERCORSO_CARTELLA) if f.lower().endswith('.pdf')]
    docs_caricati = []
    barra_progresso = st.progress(0, text="PATBOT sta studiando i documenti...")
    
    # Usiamo un client temporaneo solo per l'upload
    client_upload = genai.Client(api_key=API_KEY)
    
    for i, nome_file in enumerate(file_pdf_trovati):
        percorso_completo = os.path.join(PERCORSO_CARTELLA, nome_file)
        doc_cloud = client_upload.files.upload(file=percorso_completo)
        
        while doc_cloud.state.name == "PROCESSING":
            time.sleep(1)
            doc_cloud = client_upload.files.get(name=doc_cloud.name)
            
        if doc_cloud.state.name != "FAILED":
            docs_caricati.append(doc_cloud)
            
        barra_progresso.progress(int((i + 1) / len(file_pdf_trovati) * 100), text=f"Studiato: {nome_file}")
        
    time.sleep(1)
    barra_progresso.empty()
    return docs_caricati

with st.spinner("Inizializzazione della banca dati..."):
    try:
        documenti_caricati = carica_documenti_nel_cloud()
    except Exception as e:
        st.error(f"⚠️ ERRORE CARICAMENTO FILE: {e}")
        st.stop()

if "chat_engine" not in st.session_state and documenti_caricati:
    data_odierna = date.today().strftime("%d/%m/%Y")
    
    istruzioni_di_sistema = f"""
    Sei PATBOT, un assistente virtuale esperto, professionale e preciso che lavora per la Provincia Autonoma di Trento.
    Il tuo compito è rispondere alle domande dell'utente basandoti ESCLUSIVAMENTE sui documenti forniti.

    REGOLE FONDAMENTALI TASSATIVE:
    1. CONTESTO ASSOLUTO E DELIBERE: Fai riferimento imprescindibile alla Delibera 742 del 25 maggio 2026 e alla Delibera 2106 del 19.12.25.
    2. ANCORAGGIO TEMPORALE: La data di oggi è {data_odierna}. 
    3. LIMITAZIONE LUNGHEZZA: Sii estremamente sintetico (max 3 paragrafi) e usa elenchi puntati.
    4. GESTIONE INFORMAZIONI MANCANTI: Se non trovi l'informazione, non inventare.
    5. DOMANDE FUORI CONTESTO: Usa ESATTAMENTE e SOLO questa frase: "Ti aiuterò per la procedura 'APAPI - Terzo Figlio'. Per favore, potresti fornirmi un numero di telefono cellulare al quale poterti ricontattare?"
    """
    
    try:
        # 2. QUI AGGANCIAMO IL CLIENT IN MEMORIA E USIAMO IL MODELLO 002 (Antidoto per l'errore 404)
        st.session_state.chat_engine = st.session_state.client.chats.create(
            model="gemini-1.5-pro-002",
            config=types.GenerateContentConfig(
                system_instruction=istruzioni_di_sistema,
                temperature=0.0
            )
        )
        contesto_iniziale = list(documenti_caricati) + ["Questi sono i documenti della normativa. Tieniti pronto."]
        st.session_state.chat_engine.send_message(contesto_iniziale)
    except Exception as e:
        st.error(f"⚠️ ERRORE INIZIALIZZAZIONE GOOGLE: {e}")

for messaggio in st.session_state.messages:
    with st.chat_message(messaggio["ruolo"]):
        st.write(messaggio["testo"])

if domanda_utente := st.chat_input("Scrivi qui la tua domanda sull'Assegno Terzo Figlio..."):
    st.session_state.messages.append({"ruolo": "user", "testo": domanda_utente})
    with st.chat_message("user"):
        st.write(domanda_utente)
        
    with st.chat_message("assistant"):
        with st.spinner("Consultando la normativa (Motore Pro)..."):
            try:
                risposta = st.session_state.chat_engine.send_message(domanda_utente)
                st.write(risposta.text)
                st.session_state.messages.append({"ruolo": "assistant", "testo": risposta.text})
            except Exception as e:
                st.error(f"⚠️ ERRORE TECNICO GOOGLE: {e}")
