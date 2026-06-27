"""
Logica principale di scansione TCP.

Ogni porta viene testata con una connessione socket raw: se l'handshake TCP
a tre vie ha successo la porta viene marcata come aperta; qualsiasi errore
(refused, timeout, irraggiungibile) significa chiusa/filtrata.
Le porte vengono scansionate in parallelo tramite ThreadPoolExecutor in modo
che il timeout su una porta non blocchi le altre.
"""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable


def scan_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Tenta una connessione TCP a *host*:*port*.

    Args:
        host: Hostname o indirizzo IP del target.
        port: Numero di porta TCP (1-65535).
        timeout: Secondi di attesa prima di rinunciare.

    Returns:
        True se la porta ha accettato la connessione, False altrimenti.
    """
    try:
        # create_connection effettua risoluzione DNS + connect in una sola chiamata.
        # Il blocco 'with' garantisce che il socket venga sempre chiuso.
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        # timeout     → la porta è filtrata/il firewall sta scartando i pacchetti
        # refused     → la porta è chiusa (ricevuto RST)
        # OSError     → rete irraggiungibile, host spento, ecc.
        return False


def scan_ports(
    host: str,
    ports: list[int],
    timeout: float = 1.0,
    max_workers: int = 100,
    progress_callback: Callable[[int, bool], None] | None = None,
) -> dict[int, bool]:
    """Scansiona una lista di porte su *host* in parallelo.

    Usa un ThreadPoolExecutor in modo che tutte le prove sulle porte girino
    in modo concorrente. Il lavoro I/O-bound come le connessioni di rete
    beneficia molto dai thread anche con il GIL, perché i thread lo rilasciano
    mentre aspettano la risposta del sistema operativo.

    Args:
        host: Hostname o indirizzo IP del target.
        ports: Lista di numeri di porta da sondare.
        timeout: Timeout per singola connessione, passato a scan_port.
        max_workers: Numero massimo di thread concorrenti.
        progress_callback: Callable opzionale invocato dopo ogni risultato
            con (porta, is_open). Utile per barre di progresso in tempo reale.

    Returns:
        Dizionario che mappa ogni numero di porta a True (aperta) o False (chiusa).
    """
    results: dict[int, bool] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Sottomettiamo tutte le probe in anticipo; i futures sono indicizzati
        # per porta così possiamo recuperare il numero quando ciascuno completa.
        future_to_port = {
            executor.submit(scan_port, host, port, timeout): port
            for port in ports
        }

        # as_completed restituisce i futures nell'ordine di completamento, non
        # di sottomissione, così otteniamo i risultati appena arrivano.
        for future in as_completed(future_to_port):
            port = future_to_port[future]
            is_open = future.result()
            results[port] = is_open

            if progress_callback is not None:
                progress_callback(port, is_open)

    return results
