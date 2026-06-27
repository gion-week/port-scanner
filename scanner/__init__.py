"""
scanner — toolkit per la scansione TCP delle porte.

API pubblica (riesportata per comodità):
    scan_ports   — sonda TCP parallela di una lista di porte
    grab_banner  — legge il messaggio di benvenuto di un servizio aperto
    format_text  — output colorato per il terminale
    format_json  — output JSON machine-readable
    save_to_file — salva l'output su disco
"""

from scanner.core import scan_ports
from scanner.banner import grab_banner
from scanner.output import format_text, format_json, save_to_file

__all__ = [
    "scan_ports",
    "grab_banner",
    "format_text",
    "format_json",
    "save_to_file",
]
