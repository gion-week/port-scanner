# Esempi di scansione reale

Questa cartella raccoglie i risultati di 5 scansioni TCP reali eseguite con lo
scanner per documentare il comportamento del programma su target diversi.
Ogni scan è accompagnato dal file JSON prodotto dallo scanner e da uno screenshot
preso direttamente dalla VM di test.

---

## Ambiente di test

Tutte le scansioni sono state eseguite da una macchina virtuale con le seguenti specifiche:

| Componente | Dettaglio |
|---|---|
| **Sistema Operativo** | Parrot Security OS (basato su Debian) |
| **RAM** | 6 GB |
| **Disco** | 40 GB SSD virtuale |
| **CPU** | 2 core virtuali |
| **Hypervisor** | VMware Workstation |
| **Python** | 3.13 |

Parrot Security è una distribuzione Linux orientata alla sicurezza informatica,
frequentemente utilizzata in penetration testing e CTF. Include strumenti di analisi
di rete, ma in questo progetto lo scanner è stato scritto da zero in Python puro
per comprendere i meccanismi sottostanti.

---

## Host target

| # | Host | Tipo | Porte scansionate | Nota |
|---|---|---|---|---|
| 1 | `127.0.0.1` | Localhost | 1-1024 | Macchina locale dell'operatore |
| 2 | `scanme.nmap.org` | Host pubblico ufficiale | 22, 53, 80, 9929, 31337 | Messo a disposizione da nmap.org per test |
| 3 | `testphp.vulnweb.com` | Laboratorio vulnerabile | 21, 22, 25, 80, 443, 8080, 8443, 3306, 5432 | Server Acunetix per test di sicurezza |
| 4 | `portquiz.net` | Host "all-open" | 22, 80, 443, 3000, 8080, 8443, 9000 | Ascolta su tutte le porte TCP per design |
| 5 | `nmap.org` | Sito ufficiale nmap | 22, 25, 80, 443 | Porte comuni del sito del progetto nmap |

> **Nota legale:** Tutti gli host elencati sono pubblici e autorizzano esplicitamente
> la scansione (scanme.nmap.org, portquiz.net) oppure sono stati testati sulle sole
> porte standard senza alcuna attività invasiva. Non è stata eseguita nessuna
> exploitation né alcuna tecnica di evasione.

---

## Scan 1 — Localhost (`127.0.0.1`)

**Comando:**
```bash
python main.py 127.0.0.1 -p 1-1024 --banner
```

**Risultati:**

| Porta | Stato | Servizio identificato | Banner |
|---|---|---|---|
| 22/tcp | OPEN | SSH | `SSH-2.0-OpenSSH_10.0p2 Ubuntu-5ubuntu5.4` |
| 631/tcp | OPEN | CUPS (print server) | `CUPS/2.4 IPP/2.1` |

**File dati:** [01_localhost.json](01_localhost.json)

**Cosa dimostra questo scan:**

La scansione del loopback è il punto di partenza classico per verificare il
funzionamento dello scanner su un target controllato. Le connessioni su `127.0.0.1`
non escono dalla macchina fisica, quindi l'unica variabile è il codice dello scanner.

- **Porta 22** — SSH è il servizio di accesso remoto sicuro. Il banner
  `SSH-2.0-OpenSSH_10.0p2` rivela la versione esatta del demone: utile per
  verificare se una versione è affetta da vulnerabilità note (CVE).
- **Porta 631** — CUPS è il sistema di gestione della stampa standard su Linux.
  Ascolta su HTTP/IPP; il banner grabbing ha recuperato `CUPS/2.4 IPP/2.1`
  inviando una richiesta HTTP e leggendo la risposta. È un buon esempio di
  servizio che non invia un banner automaticamente ma risponde a una probe.

### Screenshot

> *Screenshot aggiunto dalla VM Parrot Security — vedere immagine nella cartella.*

---

## Scan 2 — scanme.nmap.org

**Comando:**
```bash
python main.py scanme.nmap.org -p 22,53,80,9929,31337 --banner -t 2.0
```

`scanme.nmap.org` è il server pubblico mantenuto dal progetto nmap specificamente
per permettere a chiunque di testare scanner e strumenti di rete.

**Risultati:**

| Porta | Stato | Servizio identificato | Banner |
|---|---|---|---|
| 22/tcp | OPEN | SSH | `SSH-2.0-OpenSSH_6.6.1p1 Ubuntu-2ubuntu2.13` |
| 53/tcp | OPEN | DNS | — (protocollo binario, no banner testuale) |
| 80/tcp | OPEN | HTTP | `HTTP/1.1 200 OK — Server: Apache/2.4.7 (Ubuntu)` |
| 9929/tcp | OPEN | ncat (echo server) | Dati binari |
| 31337/tcp | OPEN | ncat (porta di test) | — |

**File dati:** [02_scanme_nmap_org.json](02_scanme_nmap_org.json)

**Cosa dimostra questo scan:**

Questo è lo scan più ricco di informazioni e mostra tre comportamenti diversi
del banner grabbing.

- **Porta 22 (SSH):** Esempio classico di servizio che invia il banner automaticamente
  alla connessione. Il banner rivela non solo la versione SSH ma anche la distribuzione
  Linux sottostante (`Ubuntu-2ubuntu2.13`).

- **Porta 53 (DNS):** La porta è aperta ma il banner grabbing non produce nulla di
  leggibile. Il motivo è che DNS su TCP usa un formato binario con lunghezza prefissata,
  non un protocollo testuale. Questo dimostra un limite intrinseco del banner grabbing
  basato su testo.

- **Porta 80 (HTTP):** La nostra probe `HEAD / HTTP/1.0` ha ottenuto una risposta
  completa che identifica `Apache/2.4.7` su Ubuntu. Senza la probe il server non
  avrebbe inviato nulla (HTTP aspetta il client). Questo giustifica la mappa `PROBES`
  in `banner.py`.

- **Porta 9929 (ncat):** Il server ha inviato dati binari, non testo. Il nostro
  `decode("utf-8", errors="replace")` ha convertito i byte non validi in `�`
  invece di sollevare un'eccezione — lo scanner non si è mai interrotto.

- **Porta 31337 (ncat):** Porto di test aggiuntivo di scanme.nmap.org. Nessun banner,
  ma la porta è verificabilmente aperta.

### Screenshot

> *Screenshot aggiunto dalla VM Parrot Security — vedere immagine nella cartella.*

---

## Scan 3 — testphp.vulnweb.com

**Comando:**
```bash
python main.py testphp.vulnweb.com -p 21,22,25,80,443,8080,8443,3306,5432 --banner
```

`testphp.vulnweb.com` è il server vulnerabile di esempio messo a disposizione
da Acunetix per testare scanner di vulnerabilità web.

**Risultati:**

| Porta | Stato | Servizio identificato | Banner |
|---|---|---|---|
| Tutte | CLOSED | — | — |

**File dati:** [03_testphp_vulnweb_com.json](03_testphp_vulnweb_com.json)

**Cosa dimostra questo scan:**

Sebbene l'host non abbia risposto, questo scan è ugualmente utile perché mostra
due comportamenti fondamentali.

- **Target irraggiungibile o filtrato:** Il fatto che tutte le porte risultino chiuse
  non significa necessariamente che il server sia spento. Un firewall che risponde
  con RST su tutte le porte produrrà lo stesso risultato di un host non raggiungibile.
  Senza tecniche avanzate (SYN scan, UDP scan) non è distinguibile.

- **Gestione corretta degli errori:** Lo scanner ha gestito i `ConnectionRefusedError`
  su tutte le 9 porte senza eccezioni o crash, confermando la robustezza del codice.

- **Output "nessuna porta aperta":** Dimostra il path del codice in `format_text()`
  che stampa il messaggio giallo quando la lista delle porte aperte è vuota.

### Screenshot

> *Screenshot aggiunto dalla VM Parrot Security — vedere immagine nella cartella.*

---

## Scan 4 — portquiz.net

**Comando:**
```bash
python main.py portquiz.net -p 22,80,443,3000,8080,8443,9000 --banner
```

`portquiz.net` è un servizio pubblico progettato esplicitamente per testare la
connettività in uscita: ascolta su **ogni** porta TCP e risponde con una pagina HTTP.
È il target ideale per verificare che il parallelismo dello scanner funzioni
correttamente su molte porte aperte.

**Risultati:**

| Porta | Stato | Servizio identificato | Banner |
|---|---|---|---|
| 22/tcp | OPEN | — | — |
| 80/tcp | OPEN | HTTP | `HTTP/1.1 200 OK — Server: Apache/2.4.29 (Ubuntu)` |
| 443/tcp | OPEN | HTTP | `HTTP/1.1 200 OK — Server: Apache/2.4.29 (Ubuntu)` |
| 3000/tcp | OPEN | — | — |
| 8080/tcp | OPEN | HTTP | `HTTP/1.1 200 OK — Server: Apache/2.4.29 (Ubuntu)` |
| 8443/tcp | OPEN | HTTP | `HTTP/1.1 200 OK — Server: Apache/2.4.29 (Ubuntu)` |
| 9000/tcp | OPEN | — | — |

**File dati:** [04_portquiz_net.json](04_portquiz_net.json)

**Cosa dimostra questo scan:**

- **Tutte le porte aperte:** Caso opposto allo scan 3. Conferma che il motore
  `scan_ports` identifica correttamente le porte aperte quando il target risponde.

- **Banner HTTP su porte non standard:** Le porte 8080 e 8443 rispondono con lo
  stesso header Apache di 80 e 443. Questo dimostra che le nostre probe HTTP nella
  mappa `PROBES` funzionano correttamente anche su porte non standard, perché `portquiz.net`
  instrada il traffico TCP allo stesso backend HTTP indipendentemente dalla porta.

- **Porte senza banner (22, 3000, 9000):** Aperte ma silenziose. Il servizio accetta
  la connessione ma non invia dati. Il banner grabbing restituisce correttamente `None`.

### Screenshot

> *Screenshot aggiunto dalla VM Parrot Security — vedere immagine nella cartella.*

---

## Scan 5 — nmap.org

**Comando:**
```bash
python main.py nmap.org -p 22,25,80,443 --banner
```

Scan delle porte più comuni sul sito ufficiale del progetto nmap: un caso reale
di server di produzione con una superficie di attacco ridotta.

**Risultati:**

| Porta | Stato | Servizio identificato | Banner |
|---|---|---|---|
| 22/tcp | CLOSED | — | — |
| 25/tcp | CLOSED | — | — |
| 80/tcp | CLOSED | — | — |
| 443/tcp | OPEN | HTTPS | `HTTP/1.1 400 Bad Request — Server: Apache/2.4.6 (CentOS)` |

**File dati:** [05_nmap_org.json](05_nmap_org.json)

**Cosa dimostra questo scan:**

- **Superficie di attacco minima:** Solo la porta 443 è esposta. SSH e HTTP sono
  assenti dalla superficie pubblica: SSH è probabilmente raggiungibile solo da IP
  autorizzati tramite firewall, HTTP reindirizza tutto su HTTPS.

- **Banner su HTTPS con probe HTTP:** Il banner restituito è un errore `400 Bad Request`
  con il messaggio *"You're speaking plain HTTP to an SSL-enabled server"*.
  Questo accade perché la nostra probe `HEAD / HTTP/1.0` è testo in chiaro, non TLS.
  Il server risponde comunque con un messaggio HTTP in chiaro — sufficiente per
  identificare `Apache/2.4.6 (CentOS)` e la versione del sistema operativo.
  In uno scenario reale, questo richiederebbe un handshake TLS completo per
  ottenere il certificato e il banner HTTPS vero.

- **Informazioni dal banner di errore:** Anche una risposta 400 contiene dati utili.
  Il campo `Server: Apache/2.4.6 (CentOS)` indica che il server usa Apache 2.4.6
  su CentOS — una versione relativamente vecchia che un analista di sicurezza
  verificherebbe nelle liste CVE.

### Screenshot

> *Screenshot aggiunto dalla VM Parrot Security — vedere immagine nella cartella.*

---

## File presenti in questa cartella

```
esempi/
├── README.md                       # questo file
├── 01_localhost.json               # output JSON — localhost
├── 02_scanme_nmap_org.json         # output JSON — scanme.nmap.org
├── 03_testphp_vulnweb_com.json     # output JSON — testphp.vulnweb.com
├── 04_portquiz_net.json            # output JSON — portquiz.net
└── 05_nmap_org.json                # output JSON — nmap.org
```

Gli screenshot verranno aggiunti nella stessa cartella non appena eseguiti
dalla VM Parrot Security.
