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

# --- LA MODIFICA RICHIESTA: SALVIAMO IL CLIENT IN MEMORIA PER EVITARE CHIUSURE IMPROVVISE ---
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=API_KEY)

client = st.session_state.client

# La cartella sul server online
PERCORSO_CARTELLA = "normativa"

# Inizializziamo la memoria dei messaggi della chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# FUNZIONE SPECIALE: Carica i PDF su Google UNA VOLTA SOLA
@st.cache_resource(show_spinner=False)
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
    
    # Creiamo un client separato solo per caricare i file, così non intralcia la chat
    client_upload = genai.Client(api_key=API_KEY)
    
    for i, nome_file in enumerate(file_pdf_trovati):
        percorso_completo = os.path.join(PERCORSO_CARTELLA, nome_file)
        doc_cloud = client_upload.files.upload(file=percorso_completo)
        
        while doc_cloud.state.name == "PROCESSING":
            time.sleep(1)
            doc_cloud = client_upload.files.get(name=doc_cloud.name)
            
        if doc_cloud.state.name != "FAILED":
            docs_caricati.append(doc_cloud)
            
        progresso = int((i + 1) / len(file_pdf_trovati) * 100)
        barra_progresso.progress(progresso, text=f"Studiato: {nome_file}")
        
    time.sleep(1)
    barra_progresso.empty()
    return docs_caricati

with st.spinner("Inizializzazione della banca dati normativa in corso... Attendere."):
    try:
        documenti_caricati = carica_documenti_nel_cloud()
    except Exception as e:
        st.error("⚠️ Il server è momentaneamente sovraccarico per le troppe richieste. Si prega di attendere 15 minuti e ricaricare la pagina.")
        st.stop()

# Inizializziamo il motore di chat
if "chat_engine" not in st.session_state and documenti_caricati:
    data_odierna = date.today().strftime("%d/%m/%Y")
    
    istruzioni_di_sistema = f"""
    Sei PATBOT, un assistente virtuale esperto, professionale e preciso che lavora per la Provincia Autonoma di Trento.
    Il tuo compito è rispondere alle domande dell'utente basandoti ESCLUSIVAMENTE sui documenti forniti.

    REGOLE FONDAMENTALI TASSATIVE:
    
    1. CONTESTO ASSOLUTO E DELIBERE: Qualsiasi domanda ti venga posta deve essere SEMPRE considerata come riferita esclusivamente alla procedura 'APAPI - Assegno Terzo Figlio'. Per le tue risposte devi fare riferimento imprescindibile alla Delibera 742 del 25 maggio 2026 e alla Delibera 2106 del 19.12.25.
    
    2. ANCORAGGIO TEMPORALE E REGIME TRANSITORIO: La data di oggi è {data_odierna}. Considera ogni domanda come posta in questo esatto momento. Se l'utente usa un tempo futuro o un condizionale, devi interpretarla come un'ipotesi futura rispetto a oggi, applicando la normativa attualmente in vigore.
    
    3. LIMITAZIONE LUNGHEZZA E STILE: Sii estremamente sintetico, chiaro e formale. Le tue risposte non devono MAI superare i 3 paragrafi. Se la risposta è complessa, utilizza obbligatoriamente elenchi puntati per facilitare la lettura.
    
    4. GESTIONE INFORMAZIONI MANCANTI: Se la domanda è pertinente ma l'informazione specifica non è contenuta nei documenti, NON inventare nulla. Dì chiaramente: "Mi dispiace, ma non ho trovato questa informazione nella normativa ufficiale fornita."
    
    5. DOMANDE FUORI CONTESTO (OFF-TOPIC): Se l'utente ti fa una domanda completamente estranea all'argomento dell'Assegno Terzo Figlio, NON rispondere alla domanda e usa ESATTAMENTE e SOLO questa frase:
    "Ti aiuterò per la procedura 'APAPI - Terzo Figlio'. Per favore, potresti fornirmi un numero di telefono cellulare al quale poterti ricontattare?"
    """
    
    try:
        st.session_state.chat_engine = st.session_state.client.chats.create(
            model="gemini-1.5-pro",
            config=types.GenerateContentConfig(
                system_instruction=istruzioni_di_sistema,
                temperature=0.0
            )
        )
        
        contesto_iniziale = list(documenti_caricati) + ["Questi sono i documenti della normativa su cui devi basare le tue risposte. Tieniti pronto."]
        st.session_state.chat_engine.send_message(contesto_iniziale)
        
    except Exception as e:
        st.error("⚠️ Limite di comunicazioni con il server raggiunto. Attendi qualche minuto prima di usare la chat.")

for messaggio in st.session_state.messages:
    with st.chat_message(messaggio["ruolo"]):
        st.write(messaggio["testo"])

if domanda_utente := st.chat_input("Scrivi qui la tua domanda sull'Assegno Terzo Figlio..."):
    
    st.session_state.messages.append({"ruolo": "user", "testo": domanda_utente})
    with st.chat_message("user"):
        st.write(domanda_utente)
        
    with st.chat_message("assistant"):
        with st.spinner("Consultando la normativa con il motore avanzato..."):
            try:
                risposta = st.session_state.chat_engine.send_message(domanda_utente)
                st.write(risposta.text)
                st.session_state.messages.append({"ruolo": "assistant", "testo": risposta.text})
            except Exception as e:
                st.error(f"⚠️ Errore temporaneo del server Google (Possibile limite richieste superato). Riprova tra poco.")
