# Port Scanner

Scanner TCP scritto interamente in Python, senza dipendenze da tool di sistema esterni come `nmap`.
Sviluppato come progetto di portfolio nell'ambito di un percorso formativo orientato alla cybersecurity.

---

## Indice

- [Origine del progetto](#origine-del-progetto)
- [Funzionalità](#funzionalità)
- [Architettura](#architettura)
- [Scelte tecniche e loro impatto](#scelte-tecniche-e-loro-impatto)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo](#utilizzo)
- [Esempi pratici](#esempi-pratici)
- [Scansioni reali documentate](#scansioni-reali-documentate)
- [Test](#test)
- [Struttura del progetto](#struttura-del-progetto)

---

## Origine del progetto

Questo progetto nasce durante un percorso di formazione pratica in cybersecurity con l'obiettivo
di approfondire concretamente come funziona la **ricognizione di rete**, la fase iniziale di
qualsiasi valutazione della sicurezza in cui si raccolgono informazioni sull'infrastruttura target.

La domanda di partenza era semplice: cosa succede effettivamente quando uno strumento come nmap
"vede" che una porta è aperta?

La risposta è che tenta una connessione TCP. Se il sistema remoto completa l'handshake a tre vie
(SYN → SYN-ACK → ACK), la porta è aperta. Se risponde con un RST o non risponde affatto entro
un certo timeout, la porta è chiusa o filtrata. Partendo da questo principio elementare, è stato
costruito uno scanner completo in Python puro, senza invocare tool esterni, per capire ogni singolo
passaggio dall'interno.

Lo scopo è duplice: **didattico**, per consolidare la comprensione dei meccanismi di rete e della
programmazione concorrente in Python, e **professionale**, come progetto concreto da presentare
in un portfolio per ruoli nel settore della cybersecurity.

---

## Funzionalità

- Scansione TCP di singoli host, hostname o interi range di subnet (notazione CIDR)
- Specifica flessibile delle porte: singole, liste, range o combinazioni
- Scansione parallela tramite thread pool per ridurre drasticamente i tempi
- Banner grabbing opzionale per identificare il software in ascolto sulle porte aperte
- Output in formato testo colorato (terminale) o JSON (integrazione con altri tool)
- Salvataggio dell'output su file
- Configurazione via variabili d'ambiente (`.env`) senza modificare il codice

---

## Architettura

Il progetto è organizzato in moduli con responsabilità ben distinte, seguendo il
**principio di responsabilità singola**: ogni modulo fa una cosa sola e la fa bene.

```
port-scanner/
├── main.py              # Entrypoint CLI: parsing argomenti e orchestrazione
├── scanner/
│   ├── __init__.py      # Riesportazione dell'API pubblica del package
│   ├── core.py          # Logica di scansione TCP (socket + ThreadPoolExecutor)
│   ├── banner.py        # Banner grabbing sulle porte aperte
│   └── output.py        # Formattazione output (testo colorato e JSON)
├── tests/
│   ├── test_core.py     # Test unitari per la logica di scansione
│   └── test_output.py   # Test unitari per la formattazione dell'output
├── .env.example         # Variabili d'ambiente di riferimento
└── requirements.txt     # Dipendenze pinned
```

Il flusso di esecuzione è il seguente:

```
main.py
  │
  ├─ _parse_ports()     → converte "22,80-90" in [22, 80, 81, …, 90]
  ├─ _parse_hosts()     → espande "192.168.1.0/24" nei 254 indirizzi host
  │
  └─ per ogni host:
       │
       ├─ scan_ports()  → lancia N thread, uno per porta
       │    └─ scan_port()  → socket.create_connection() → True/False
       │
       ├─ grab_banner() → (opzionale) legge il greeting del servizio
       │
       └─ format_text() / format_json() → stampa e/o salva su file
```

---

## Scelte tecniche e loro impatto

Questa sezione spiega il *perché* dietro le principali decisioni di progettazione
e come ciascuna influisce concretamente sul comportamento dello scanner.

### 1. Socket TCP raw invece di librerie di alto livello

Lo scanner usa direttamente `socket.create_connection()` dalla stdlib di Python,
senza librerie di terze parti per la scansione di rete.

**Perché:** Mantiene il codice completamente trasparente e leggibile. Non esiste
"magia" nascosta dietro un'astrazione: ogni riga di codice corrisponde a un'operazione
di rete ben definita. In un contesto didattico, questo è fondamentale per capire
cosa sta succedendo realmente.

**Impatto sul funzionamento:** Lo scanner esegue una **connessione TCP completa**
(full connect scan). Questo significa che:

- È rilevabile dai log del sistema target, perché la connessione viene stabilita davvero
- Non richiede privilegi di root (a differenza delle tecniche SYN-scan che richiedono
  la costruzione manuale di pacchetti raw)
- È affidabile: se la connessione riesce, la porta è *certamente* aperta

### 2. ThreadPoolExecutor per la scansione parallela

Le connessioni di rete sono operazioni **I/O-bound**: il codice passa la maggior
parte del tempo ad aspettare la risposta del sistema operativo, non a eseguire calcoli.

**Perché i thread funzionano bene qui (nonostante il GIL):** Il Global Interpreter Lock
di Python impedisce l'esecuzione parallela di codice Python puro, ma *lo rilascia*
durante le chiamate di sistema bloccanti come `connect()` e `recv()`. Questo significa
che con 100 thread, i timeout di 1 secondo girano effettivamente in parallelo.

**Impatto pratico:**

| Modalità | 1024 porte, timeout 1s |
|---|---|
| Sequenziale | ~17 minuti (1024 × 1s) |
| 100 thread | ~10-15 secondi |
| 200 thread | ~5-10 secondi |

Il parametro `--workers` permette di bilanciare velocità e carico sulla rete.
Valori troppo alti (> 500) possono causare errori "too many open files" o
saturare la connessione di rete locale.

### 3. `as_completed()` invece di raccogliere tutti i risultati alla fine

Il codice usa `concurrent.futures.as_completed()` per elaborare i risultati
non appena arrivano, invece di aspettare che tutti i thread terminino.

**Perché:** Rende possibile implementare una barra di progresso in tempo reale
tramite il parametro `progress_callback`. Semanticamente, rispecchia meglio
il processo reale: i risultati arrivano in ordine casuale e vengono registrati
subito, non in blocco alla fine.

### 4. Banner grabbing con probe specifiche per porta

Il banner grabbing non usa un approccio uniforme per tutte le porte.
Il modulo `banner.py` distingue due categorie di servizi:

- **Servizi che parlano per primi** (SSH, FTP, SMTP, POP3): inviano automaticamente
  un banner di benvenuto non appena il client si connette. È sufficiente aprire la
  connessione e leggere.

- **Servizi che aspettano il client** (HTTP su porte 80, 443, 8080, 8443): rimangono
  in silenzio finché non ricevono una richiesta valida. Per questi viene inviata
  una probe `HEAD / HTTP/1.0\r\n\r\n` prima di leggere la risposta.

**Impatto:** Senza questa distinzione, le porte HTTP restituirebbero sempre `None`
come banner, anche se il servizio è attivo e identificabile.

### 5. Decodifica UTF-8 con `errors="replace"`

I banner vengono decodificati con `raw.decode("utf-8", errors="replace")`.

**Perché:** Alcuni servizi usano protocolli binari o inviano byte non validi
in UTF-8. Con `errors="replace"`, i byte non decodificabili vengono sostituiti
con il carattere di sostituzione Unicode (U+FFFD, ``) invece di sollevare
un'eccezione `UnicodeDecodeError`. Lo scanner non si interrompe mai per dati
inattesi da un servizio sconosciuto.

### 6. Separazione output testuale / JSON

La logica di formattazione è completamente separata dalla logica di scansione
nel modulo `output.py`.

**Perché:** Seguendo il principio Open/Closed, aggiungere un nuovo formato di
output (es. CSV, XML) non richiede di toccare `core.py` o `banner.py`. I due
formati soddisfano usi diversi: il testo colorato è pensato per l'analisi umana
interattiva; il JSON è pensato per essere consumato da script, pipeline CI/CD
o altri strumenti di analisi.

### 7. Configurazione via `.env` e `python-dotenv`

Timeout e numero di worker sono configurabili tramite variabili d'ambiente
invece di essere hardcoded.

**Perché:** Consente di adattare il comportamento dello scanner a contesti diversi
(rete lenta → timeout maggiore, macchina potente → più worker) senza modificare
il codice sorgente e senza passare ogni volta i flag da riga di comando.
È anche una buona pratica per non esporre mai valori di configurazione sensibili
nel codice versionato.

---

## Installazione

**Prerequisiti:** Python 3.10 o superiore, `git`

```bash
# 1. Clona il repository
git clone <url-del-repository>
cd port-scanner

# 2. Crea e attiva il virtual environment
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Installa le dipendenze
pip install -r requirements.txt
```

---

## Configurazione

Copia il file di esempio e personalizzalo:

```bash
cp .env.example .env
```

Le variabili disponibili sono:

| Variabile | Default | Descrizione |
|---|---|---|
| `SCAN_TIMEOUT` | `1.0` | Secondi di attesa per ogni connessione TCP |
| `SCAN_MAX_WORKERS` | `100` | Numero massimo di thread paralleli |

I valori nel `.env` vengono sovrascitti dai flag passati da riga di comando.

---

## Utilizzo

```
python main.py <target> [opzioni]
```

### Argomenti posizionali

| Argomento | Descrizione |
|---|---|
| `target` | IP, hostname o range CIDR (es. `192.168.1.0/24`) |

### Opzioni

| Flag | Default | Descrizione |
|---|---|---|
| `-p`, `--ports PORTE` | `1-1024` | Porte da scansionare |
| `-t`, `--timeout SECONDI` | `1.0` | Timeout per connessione |
| `-w`, `--workers N` | `100` | Thread paralleli massimi |
| `--banner` | disabilitato | Abilita il banner grabbing |
| `--format {text,json}` | `text` | Formato di output |
| `-o`, `--output FILE` | — | Salva l'output su file |

### Sintassi per le porte

```
-p 80              # porta singola
-p 22,80,443       # lista di porte
-p 1-1024          # range
-p 22,80-90,443    # combinazione
-p 1-65535         # tutte le porte
```

---

## Esempi pratici

```bash
# Scansione base delle porte più comuni su un host
python main.py 192.168.1.1

# Scansione di porte specifiche con banner grabbing
python main.py 192.168.1.1 -p 21,22,25,80,443 --banner

# Output JSON salvato su file
python main.py 192.168.1.1 -p 1-1024 --format json -o risultati.json

# Scansione rapida di una subnet (tutte le porte comuni)
python main.py 192.168.1.0/24 -p 22,80,443,3389 -t 0.3 -w 200

# Scansione completa con timeout generoso (rete lenta o VPN)
python main.py 10.0.0.1 -p 1-65535 -t 2.0 -w 150 --banner

# Scansione di un hostname pubblico
python main.py scanme.nmap.org -p 22,80 --banner
```

### Esempio di output testuale

```
Scansione di 1 host, 4 porte [timeout=1.0s, workers=100]

Risultati scansione per 192.168.1.1
PORTA      STATO    BANNER
------------------------------------------------------------
22         open     SSH-2.0-OpenSSH_9.3
80         open     HTTP/1.1 200 OK...

3 porta/e chiusa/e non mostrata/e.
```

### Esempio di output JSON

```json
{
  "host": "192.168.1.1",
  "ports": {
    "22": {
      "state": "open",
      "banner": "SSH-2.0-OpenSSH_9.3"
    },
    "80": {
      "state": "open",
      "banner": null
    },
    "443": {
      "state": "closed",
      "banner": null
    }
  }
}
```

---

## Scansioni reali documentate

La cartella [`esempi/`](esempi/) contiene i risultati di 5 scansioni TCP reali
eseguite dallo scanner su target diversi, con analisi dei risultati e spiegazione
di cosa dimostra ogni caso.

| # | Target | Porte | Risultato chiave |
|---|---|---|---|
| 1 | `127.0.0.1` (localhost) | 1-1024 | SSH:22, CUPS:631 |
| 2 | `scanme.nmap.org` | 22, 53, 80, 9929, 31337 | 5 porte aperte, banner SSH + HTTP + dati binari |
| 3 | `testphp.vulnweb.com` | 9 porte comuni | Tutte chiuse — caso host filtrato |
| 4 | `portquiz.net` | 22, 80, 443, 3000, 8080, 8443, 9000 | Tutte aperte (host "all-open" by design) |
| 5 | `nmap.org` | 22, 25, 80, 443 | Solo 443 aperto, banner Apache/CentOS da probe HTTP |

Ogni scan include:
- Il comando esatto utilizzato
- La tabella dei risultati con porte, stato e banner
- Il file JSON prodotto dallo scanner
- L'analisi di cosa dimostra il caso specifico
- Uno screenshot dalla VM Parrot Security

→ **[Leggi la documentazione completa degli esempi](esempi/README.md)**

---

## Test

Il progetto include una suite di 25 test unitari. Tutti i test usano mock per
simulare le connessioni di rete, quindi girano senza accesso alla rete e in
meno di un secondo.

```bash
# Eseguire tutti i test
pytest tests/

# Output verboso (mostra il nome di ogni test)
pytest tests/ -v

# Eseguire solo i test di un modulo
pytest tests/test_core.py -v
pytest tests/test_output.py -v
```

### Copertura dei test

**`test_core.py`** — verifica la logica di scansione:
- `scan_port` restituisce `True` su connessione riuscita
- `scan_port` restituisce `False` su `ConnectionRefusedError`, `socket.timeout`, `OSError`
- Il timeout viene passato correttamente a `create_connection`
- `scan_ports` restituisce un risultato per ogni porta richiesta
- Le porte aperte vengono correttamente identificate
- Il `progress_callback` viene invocato una volta per porta
- Una lista vuota produce un dizionario vuoto senza errori

**`test_output.py`** — verifica la formattazione:
- `format_json` produce JSON valido con la struttura attesa
- I campi `host`, `state` e `banner` sono corretti per porte aperte e chiuse
- `format_text` include i numeri di porta, i banner e l'host nell'header
- Il messaggio "nessuna porta aperta" appare quando tutto è chiuso
- `save_to_file` scrive, sovrascrive e crea file correttamente

---

## Struttura del progetto

```
port-scanner/
├── main.py              # CLI: argparse, orchestrazione, I/O su file
├── scanner/
│   ├── __init__.py      # Riesporta l'API pubblica del package
│   ├── core.py          # scan_port() + scan_ports() con ThreadPoolExecutor
│   ├── banner.py        # grab_banner() con probe specifiche per protocollo
│   └── output.py        # format_text(), format_json(), save_to_file()
├── tests/
│   ├── __init__.py
│   ├── test_core.py     # 10 test per scanner.core
│   └── test_output.py   # 15 test per scanner.output
├── esempi/
│   ├── README.md                   # documentazione degli scan reali + VM specs
│   ├── 01_localhost.json           # scan localhost 1-1024
│   ├── 02_scanme_nmap_org.json     # scan scanme.nmap.org
│   ├── 03_testphp_vulnweb_com.json # scan testphp.vulnweb.com (tutte chiuse)
│   ├── 04_portquiz_net.json        # scan portquiz.net (tutte aperte)
│   └── 05_nmap_org.json            # scan nmap.org
├── .env.example         # Template variabili d'ambiente
├── .gitignore
├── requirements.txt
└── README.md
```

---

> **Nota legale:** Questo strumento è sviluppato esclusivamente per scopi didattici
> e per test su sistemi di propria proprietà o per cui si dispone di autorizzazione
> scritta. La scansione di porte su sistemi altrui senza consenso è illegale in molti
> paesi. L'autore non si assume responsabilità per usi impropri.
