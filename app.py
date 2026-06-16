import streamlit as st
import os
import time
from datetime import date
from google import genai
from google.genai import types

# Configurazione grafica della pagina web
st.set_page_config(page_title="PATBOT - Assistente Normativa", page_icon="🤖")
st.title("🤖 PATBOT - Assistente Normativa")
st.subheader("Procedura 'APAPI - Terzo Figlio'")
st.write("Fai una domanda sulla normativa provinciale. Il bot risponderà basandosi sui documenti ufficiali.")

# 1. RECUPERO DELLA CHIAVE DALLA CASSAFORTE SEGRETA DI STREAMLIT
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ Configurazione incompleta: Chiave API non trovata nella cassaforte (Secrets)!")
    st.stop()

client = genai.Client(api_key=API_KEY)

# La cartella sul server online sarà semplicemente quella in cui metteremo i file su GitHub
PERCORSO_CARTELLA = "normativa"

# Inizializziamo la memoria dei messaggi della chat se non esiste
if "messages" not in st.session_state:
    st.session_state.messages = []

# FUNZIONE SPECIALE: Carica i PDF su Google UNA VOLTA SOLA e li tiene in memoria
@st.cache_resource
def carica_documenti_nel_cloud():
    if not os.path.exists(PERCORSO_CARTELLA):
        st.error(f"Errore: la cartella '{PERCORSO_CARTELLA}' non esiste!")
        return []
    
    file_pdf_trovati = [f for f in os.listdir(PERCORSO_CARTELLA) if f.lower().endswith('.pdf')]
    if not file_pdf_trovati:
        st.error("Errore: nessun file PDF trovato nella cartella!")
        return []
        
    docs_caricati = []
    barra_progresso = st.progress(0, text="PATBOT sta studiando i documenti normativi...")
    
    for i, nome_file in enumerate(file_pdf_trovati):
        percorso_completo = os.path.join(PERCORSO_CARTELLA, nome_file)
        doc_cloud = client.files.upload(file=percorso_completo)
        
        while doc_cloud.state.name == "PROCESSING":
            time.sleep(1)
            doc_cloud = client.files.get(name=doc_cloud.name)
            
        if doc_cloud.state.name != "FAILED":
            docs_caricati.append(doc_cloud)
            
        progresso = int((i + 1) / len(file_pdf_trovati) * 100)
        barra_progresso.progress(progresso, text=f"Studiato: {nome_file}")
        
    time.sleep(1)
    barra_progresso.empty() # Cancella la barra quando ha finito
    return docs_caricati

# Avviamo lo studio dei documenti (sfruttando la memoria intelligente di Streamlit)
documenti_caricati = carica_documenti_nel_cloud()

# Inizializziamo il motore di chat se non è già attivo
if "chat_engine" not in st.session_state and documenti_caricati:
    data_odierna = date.today().strftime("%d/%m/%Y")
    
    istruzioni_di_sistema = f"""
    Sei PATBOT, un assistente virtuale esperto, professionale e preciso che lavora per la Provincia.
    Il tuo compito è rispondere alle domande dell'utente basandoti ESCLUSIVAMENTE sui documenti forniti. 

    REGOLE FONDAMENTALI:
    1. GESTIONE INFORMAZIONI MANCANTI: Se la domanda è pertinente ma l'informazione specifica non è contenuta nei documenti, NON inventare nulla (niente allucinazioni). Dì chiaramente: "Mi dispiace, ma non ho trovato questa informazione nella normativa."

    2. ATTENZIONE AL REGIME TRANSITORIO: La data di oggi è {data_odierna}. 
    Devi sempre confrontare questa data con le date di validità indicate nei PDF. Se ci troviamo all'interno di un periodo transitorio, dai priorità assoluta alle regole di quel regime e fallo presente all'utente (es. "Attenzione, in base alla normativa transitoria attualmente in vigore...").

    3. DOMANDE FUORI CONTESTO (OFF-TOPIC): Se l'utente ti fa una domanda completamente estranea all'argomento della normativa provinciale (ad esempio domande di cultura generale, meteo, chiacchiere inutili o richieste di aiuto su procedure non documentate), non rispondere alla domanda. Rispondi ESATTAMENTE e SOLO con questa frase:
    "Ti aiuterò per la procedura 'APAPI - Terzo Figlio'. Per favore, potresti fornirmi un numero di telefono cellulare al quale poterti ricontattare?"
    """
    
    # Creiamo la sessione di chat con Google
    st.session_state.chat_engine = client.chats.create(
        model="gemini-3.1-pro",
        config=types.GenerateContentConfig(system_instruction=istruzioni_di_sistema)
    )
    
    # Iniettiamo i documenti
    contesto_iniziale = list(documenti_caricati) + ["Questi sono i documenti della normativa su cui devi basare le tue risposte. Tieniti pronto."]
    st.session_state.chat_engine.send_message(contesto_iniziale)

# Mostriamo a schermo i messaggi precedenti della chat (stile WhatsApp)
for messaggio in st.session_state.messages:
    with st.chat_message(messaggio["ruolo"]):
        st.write(messaggio["testo"])

# Gestione della nuova domanda inserita dall'utente
if domanda_utente := st.chat_input("Scrivi qui la tua domanda..."):
    
    # Mostriamo la domanda dell'utente
    st.session_state.messages.append({"ruolo": "user", "testo": domanda_utente})
    with st.chat_message("user"):
        st.write(domanda_utente)
        
    # Generiamo la risposta del bot
    with st.chat_message("assistant"):
        with st.spinner("Sto consultando la normativa..."):
            try:
                risposta = st.session_state.chat_engine.send_message(domanda_utente)
                st.write(risposta.text)
                st.session_state.messages.append({"ruolo": "assistant", "testo": risposta.text})
            except Exception as e:
                st.error(f"Si è verificato un errore nella generazione della risposta: {e}")
