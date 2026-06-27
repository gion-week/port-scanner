"""
Formattazione dell'output per i risultati della scansione.

Mantiene la logica di presentazione completamente separata dalla logica di
scansione in modo che lo stesso dizionario di risultati possa essere reso
come testo colorato per il terminale oppure come JSON machine-readable per
script e pipeline.
"""

import json

from colorama import Fore, Style, init as _colorama_init

# autoreset=True significa che non dobbiamo reimpostare manualmente il colore
# dopo ogni stringa colorata; colorama aggiunge il codice di reset automaticamente.
_colorama_init(autoreset=True)

# Alias di tipo per il risultato di una singola porta.
PortResult = dict  # {"open": bool, "banner": str | None}


def format_text(host: str, results: dict[int, PortResult]) -> str:
    """Rende i risultati della scansione come stringa colorata leggibile nel terminale.

    Le porte aperte vengono stampate in verde; le porte chiuse vengono
    riassunte in un'unica riga in fondo per evitare di inondare il terminale.

    Args:
        host: Hostname o IP scansionato (mostrato nell'intestazione).
        results: Mappa porta → {"open": bool, "banner": str | None}.

    Returns:
        Stringa multiriga pronta per essere stampata.
    """
    lines: list[str] = [
        f"\n{Style.BRIGHT}Risultati scansione per {host}{Style.RESET_ALL}"
    ]

    open_ports = sorted(
        ((port, data) for port, data in results.items() if data["open"]),
        key=lambda x: x[0],
    )
    closed_count = sum(1 for data in results.values() if not data["open"])

    if not open_ports:
        lines.append(f"{Fore.YELLOW}  Nessuna porta aperta trovata.")
    else:
        lines.append(f"{'PORTA':<10} {'STATO':<8} BANNER")
        lines.append("-" * 60)
        for port, data in open_ports:
            banner = data.get("banner") or ""
            # Tronchiamo i banner lunghi per mantenere la tabella leggibile.
            if len(banner) > 60:
                banner = banner[:57] + "..."
            lines.append(
                f"{Fore.GREEN}{port:<10} {'open':<8}{Style.RESET_ALL} {banner}"
            )

    lines.append(f"\n{closed_count} porta/e chiusa/e non mostrata/e.")
    return "\n".join(lines)


def format_json(host: str, results: dict[int, PortResult]) -> str:
    """Rende i risultati della scansione come JSON indentato.

    La struttura JSON è progettata per essere facilmente consumabile da altri
    strumenti: una chiave 'host' di primo livello e un oggetto 'ports'
    indicizzato per numero di porta.

    Args:
        host: Hostname o IP scansionato.
        results: Mappa porta → {"open": bool, "banner": str | None}.

    Returns:
        Stringa JSON ben formattata.
    """
    payload = {
        "host": host,
        "ports": {
            # Le chiavi JSON devono essere stringhe; ordiniamo numericamente per leggibilità.
            str(port): {
                "state": "open" if data["open"] else "closed",
                "banner": data.get("banner"),
            }
            for port, data in sorted(results.items())
        },
    }
    return json.dumps(payload, indent=2)


def save_to_file(content: str, filepath: str) -> None:
    """Scrive *content* in *filepath*, sovrascrivendo qualsiasi file esistente.

    Args:
        content: Il testo da scrivere (testo semplice o stringa JSON).
        filepath: Percorso di destinazione su disco.
    """
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)
