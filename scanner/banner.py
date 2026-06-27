"""
Banner grabbing per le porte aperte.

Molti servizi di rete inviano un messaggio di benvenuto (banner) immediatamente
dopo che un client si connette, oppure in risposta a una semplice probe.
Leggere quel banner ci permette di identificare il software e la versione in
esecuzione sulla porta senza strumenti esterni.

Esempi:
    SSH       → "SSH-2.0-OpenSSH_9.3"
    FTP       → "220 vsftpd 3.0.5"
    SMTP      → "220 mail.example.com ESMTP Postfix"
    HTTP      → invia una HEAD ed estrae l'header Server della risposta
    CUPS/IPP  → "CUPS/2.4 IPP/2.1" (porta 631, gestita come una porta web)
"""

import socket

# Porte che richiedono una probe esplicita per produrre una risposta.
# La maggior parte dei protocolli testuali (SSH, FTP, SMTP) invia il banner
# automaticamente; HTTP ha bisogno di almeno una riga di richiesta valida.
_HTTP_PROBE = b"HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n"

PROBES: dict[int, bytes] = {
    80: _HTTP_PROBE,
    443: _HTTP_PROBE,
    # CUPS (porta 631) parla HTTP/IPP: come una porta web resta in silenzio
    # finché non riceve una richiesta, quindi va sondato con la stessa probe.
    631: _HTTP_PROBE,
    8080: _HTTP_PROBE,
    8443: _HTTP_PROBE,
}

# Numero massimo di byte da leggere dal banner di risposta.
_READ_SIZE = 1024


def _extract_http_server(text: str) -> str | None:
    """Estrae il valore dell'header ``Server:`` da una risposta HTTP.

    CUPS, Apache, nginx e simili rispondono a una probe HTTP con un header
    ``Server:`` che identifica software e versione (es. ``CUPS/2.4 IPP/2.1``).
    Restituire solo quel valore tiene la tabella dei risultati compatta invece
    di stampare l'intera risposta grezza multiriga.

    Args:
        text: Risposta HTTP decodificata (status line + header).

    Returns:
        Il valore dell'header ``Server`` senza spazi, oppure None se assente.
    """
    for line in text.splitlines():
        if line.lower().startswith("server:"):
            return line.split(":", 1)[1].strip() or None
    return None


def grab_banner(host: str, port: int, timeout: float = 2.0) -> str | None:
    """Tenta di leggere il banner del servizio da una porta già nota come aperta.

    La funzione si connette, invia opzionalmente una probe, poi legge fino a
    1 KB di risposta. Se il servizio è lento o non risponde, il timeout
    evita di bloccare l'intera scansione.

    Args:
        host: Hostname o indirizzo IP del target.
        port: Numero di porta TCP del servizio aperto.
        timeout: Secondi di attesa per una risposta dopo la connessione.

    Returns:
        Il testo del banner senza spazi iniziali/finali, oppure None in caso di errore.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            probe = PROBES.get(port)
            if probe:
                sock.sendall(probe)

            # Applichiamo il timeout anche alla chiamata recv così i servizi
            # lenti non bloccano l'intera scansione.
            sock.settimeout(timeout)
            raw = sock.recv(_READ_SIZE)

        # Decodifichiamo come UTF-8 sostituendo i byte non validi (protocolli
        # binari, dati corrotti) così non solleviamo mai un'eccezione qui.
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return None

        # Per le risposte HTTP (CUPS/IPP incluso) estraiamo l'header Server,
        # che identifica il servizio in modo compatto (es. 'CUPS/2.4 IPP/2.1').
        # Se manca, ripieghiamo sulla status line (prima riga).
        if text.startswith("HTTP/"):
            return _extract_http_server(text) or text.splitlines()[0]

        return text

    except (socket.timeout, ConnectionRefusedError, OSError):
        return None
