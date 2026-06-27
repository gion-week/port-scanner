#!/usr/bin/env python3
"""
Port Scanner — entrypoint da riga di comando.

Esempi d'uso:
    # Scansiona le porte 1-1024 su un singolo host (output testuale)
    python main.py 192.168.1.1

    # Scansiona porte specifiche con banner grabbing
    python main.py scanme.nmap.org -p 22,80,443 --banner

    # Scansiona una subnet e salva l'output in JSON
    python main.py 192.168.1.0/24 -p 22,80 --format json -o risultati.json

    # Avanzato: 200 thread, timeout di 2 secondi
    python main.py 10.0.0.1 -p 1-65535 -w 200 -t 2.0
"""

import argparse
import ipaddress
import os

from dotenv import load_dotenv

from scanner.core import scan_ports
from scanner.banner import grab_banner
from scanner.output import format_text, format_json

# Carichiamo il file .env così gli utenti possono impostare SCAN_TIMEOUT /
# SCAN_MAX_WORKERS senza passare i flag ogni volta.
load_dotenv()

_DEFAULT_TIMEOUT = float(os.getenv("SCAN_TIMEOUT", "1.0"))
_DEFAULT_WORKERS = int(os.getenv("SCAN_MAX_WORKERS", "100"))


# ---------------------------------------------------------------------------
# Funzioni di supporto per il parsing degli argomenti
# ---------------------------------------------------------------------------

def _parse_ports(port_str: str) -> list[int]:
    """Converte un'espressione di porte in una lista ordinata di interi.

    Formati supportati:
        "80"          → [80]
        "80,443,8080" → [80, 443, 8080]
        "1-1024"      → [1, 2, …, 1024]
        "22,80-90"    → [22, 80, 81, …, 90]

    Args:
        port_str: Stringa grezza dall'argomento -p / --ports.

    Returns:
        Lista ordinata e deduplicata di numeri di porta.

    Raises:
        argparse.ArgumentTypeError: Se un token è invalido o fuori range.
    """
    ports: list[int] = []
    for token in port_str.split(","):
        token = token.strip()
        try:
            if "-" in token:
                lo, hi = token.split("-", 1)
                lo_int, hi_int = int(lo), int(hi)
                if not (1 <= lo_int <= hi_int <= 65535):
                    raise ValueError
                ports.extend(range(lo_int, hi_int + 1))
            else:
                p = int(token)
                if not (1 <= p <= 65535):
                    raise ValueError
                ports.append(p)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Specifica di porta non valida: '{token}'. "
                "Usa numeri 1-65535, range come '80-443', o liste separate da virgole."
            )
    return sorted(set(ports))


def _parse_hosts(target: str) -> list[str]:
    """Espande *target* in una lista di host da scansionare.

    Un CIDR come "192.168.1.0/24" diventa tutti i 254 indirizzi host.
    Un IP o hostname semplice viene restituito così com'è in una lista
    con un solo elemento.

    Args:
        target: Indirizzo IP, hostname o notazione CIDR.

    Returns:
        Lista di stringhe host.
    """
    try:
        # strict=False permette "192.168.1.5/24" (bit host impostati) senza errore.
        network = ipaddress.ip_network(target, strict=False)
        hosts = [str(ip) for ip in network.hosts()]
        # /32 (singolo host) → network.hosts() è vuoto; usiamo l'indirizzo di rete.
        return hosts if hosts else [str(network.network_address)]
    except ValueError:
        # Non è un IP/CIDR → trattato come hostname (la risoluzione DNS avviene nel socket).
        return [target]


# ---------------------------------------------------------------------------
# Funzione principale
# ---------------------------------------------------------------------------

def main() -> None:
    """Analizza gli argomenti, esegue la scansione e stampa / salva i risultati."""
    parser = argparse.ArgumentParser(
        prog="port-scanner",
        description="Scanner TCP per porte con banner grabbing opzionale.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "target",
        help="Indirizzo IP, hostname o range CIDR (es. 192.168.1.0/24)",
    )
    parser.add_argument(
        "-p", "--ports",
        default="1-1024",
        metavar="PORTE",
        help="Porte da scansionare. Esempi: 80  |  22,80,443  |  1-65535  (default: 1-1024)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT,
        metavar="SECONDI",
        help=f"Timeout per connessione in secondi (default: {_DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=_DEFAULT_WORKERS,
        metavar="N",
        help=f"Numero massimo di thread paralleli (default: {_DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--banner",
        action="store_true",
        help="Tenta il banner grabbing sulle porte aperte",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Formato di output: 'text' (colorato, leggibile) o 'json' (default: text)",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Salva l'output in FILE oltre a stamparlo",
    )

    args = parser.parse_args()

    # --- risoluzione target e porte ------------------------------------------
    try:
        ports = _parse_ports(args.ports)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
        return  # irraggiungibile; mantiene il type checker soddisfatto

    hosts = _parse_hosts(args.target)

    print(
        f"Scansione di {len(hosts)} host, {len(ports)} porte "
        f"[timeout={args.timeout}s, workers={args.workers}]"
    )

    # --- scansione di ogni host -----------------------------------------------
    for host in hosts:
        print(f"  → {host} ...", end="\r", flush=True)

        port_states: dict[int, bool] = scan_ports(
            host,
            ports,
            timeout=args.timeout,
            max_workers=args.workers,
        )

        # Costruiamo il dizionario arricchito aggiungendo il banner se richiesto.
        results: dict[int, dict] = {}
        for port, is_open in port_states.items():
            banner: str | None = None
            if is_open and args.banner:
                # Usiamo un timeout leggermente maggiore per la lettura del banner.
                banner = grab_banner(host, port, timeout=args.timeout * 2)
            results[port] = {"open": is_open, "banner": banner}

        # --- formattazione dell'output ----------------------------------------
        if args.format == "json":
            output = format_json(host, results)
        else:
            output = format_text(host, results)

        print(output)

        if args.output:
            # Append quando scansionando più host; sovrascriviamo per host singolo.
            mode = "a" if len(hosts) > 1 else "w"
            with open(args.output, mode, encoding="utf-8") as fh:
                fh.write(output + "\n")

    if args.output:
        print(f"\nOutput salvato in: {args.output}")


if __name__ == "__main__":
    main()
