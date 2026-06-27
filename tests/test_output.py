"""
Test per scanner.output — formattazione dei risultati.

Testiamo la struttura e il contenuto dell'output senza fare asserzioni sui
codici ANSI di colorazione, perché sono visivi e renderebbero i test fragili.
"""

import json

import pytest

from scanner.output import format_text, format_json, save_to_file


# ---------------------------------------------------------------------------
# Dati condivisi tra i test
# ---------------------------------------------------------------------------

SAMPLE_RESULTS: dict[int, dict] = {
    22:   {"open": True,  "banner": "SSH-2.0-OpenSSH_9.3"},
    80:   {"open": True,  "banner": None},
    9999: {"open": False, "banner": None},
}

ALL_CLOSED: dict[int, dict] = {
    1000: {"open": False, "banner": None},
    2000: {"open": False, "banner": None},
}


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------

class TestFormatJson:
    """Test per format_json()."""

    def test_produces_valid_json(self):
        """L'output deve essere analizzabile da json.loads senza errori."""
        output = format_json("127.0.0.1", SAMPLE_RESULTS)
        json.loads(output)  # solleva se il JSON non è valido

    def test_host_field_is_correct(self):
        """La chiave 'host' di primo livello deve corrispondere all'argomento passato."""
        data = json.loads(format_json("10.0.0.1", SAMPLE_RESULTS))
        assert data["host"] == "10.0.0.1"

    def test_open_port_state(self):
        """Una porta aperta deve avere state='open'."""
        data = json.loads(format_json("127.0.0.1", SAMPLE_RESULTS))
        assert data["ports"]["22"]["state"] == "open"

    def test_closed_port_state(self):
        """Una porta chiusa deve avere state='closed'."""
        data = json.loads(format_json("127.0.0.1", SAMPLE_RESULTS))
        assert data["ports"]["9999"]["state"] == "closed"

    def test_banner_included_when_present(self):
        """La stringa banner viene preservata nell'output JSON."""
        data = json.loads(format_json("127.0.0.1", SAMPLE_RESULTS))
        assert data["ports"]["22"]["banner"] == "SSH-2.0-OpenSSH_9.3"

    def test_banner_is_null_when_absent(self):
        """Il banner è null in JSON quando viene fornito None."""
        data = json.loads(format_json("127.0.0.1", SAMPLE_RESULTS))
        assert data["ports"]["80"]["banner"] is None

    def test_all_ports_present(self):
        """Ogni porta scansionata appare nell'output, aperta o chiusa."""
        data = json.loads(format_json("127.0.0.1", SAMPLE_RESULTS))
        assert set(data["ports"].keys()) == {"22", "80", "9999"}


# ---------------------------------------------------------------------------
# format_text
# ---------------------------------------------------------------------------

class TestFormatText:
    """Test per format_text()."""

    def test_open_port_numbers_appear_in_output(self):
        """I numeri delle porte aperte devono essere visibili nell'output testuale."""
        output = format_text("127.0.0.1", SAMPLE_RESULTS)
        assert "22" in output
        assert "80" in output

    def test_banner_appears_when_present(self):
        """Il banner del servizio viene mostrato accanto alla riga della porta."""
        output = format_text("127.0.0.1", SAMPLE_RESULTS)
        assert "SSH-2.0-OpenSSH_9.3" in output

    def test_host_appears_in_header(self):
        """L'host target viene menzionato nell'intestazione dell'output."""
        output = format_text("192.168.1.1", SAMPLE_RESULTS)
        assert "192.168.1.1" in output

    def test_no_open_ports_message(self):
        """Viene mostrato un messaggio 'nessuna porta aperta' quando tutto è chiuso."""
        output = format_text("127.0.0.1", ALL_CLOSED)
        assert "Nessuna porta aperta" in output

    def test_closed_count_line_present(self):
        """Una riga di riepilogo conta le porte chiuse."""
        output = format_text("127.0.0.1", SAMPLE_RESULTS)
        assert "chiusa" in output.lower()


# ---------------------------------------------------------------------------
# save_to_file
# ---------------------------------------------------------------------------

class TestSaveToFile:
    """Test per save_to_file()."""

    def test_writes_content_to_disk(self, tmp_path):
        """Il contenuto scritto da save_to_file è leggibile dal disco."""
        path = str(tmp_path / "scan.txt")
        save_to_file("ciao mondo", path)
        assert open(path, encoding="utf-8").read() == "ciao mondo"

    def test_overwrites_existing_file(self, tmp_path):
        """Chiamare save_to_file due volte sostituisce il contenuto precedente."""
        path = str(tmp_path / "scan.txt")
        save_to_file("primo", path)
        save_to_file("secondo", path)
        assert open(path, encoding="utf-8").read() == "secondo"

    def test_creates_file_if_not_exists(self, tmp_path):
        """save_to_file crea il file se non esiste ancora."""
        path = str(tmp_path / "nuovo_file.json")
        save_to_file("{}", path)
        assert open(path, encoding="utf-8").read() == "{}"
