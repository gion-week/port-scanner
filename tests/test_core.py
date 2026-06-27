"""
Test per scanner.core — logica di scansione TCP.

Tutti i test usano unittest.mock per evitare connessioni di rete reali.
Questo rende i test veloci (nessun timeout), deterministici e sicuri da
eseguire in qualsiasi ambiente, inclusi CI senza accesso alla rete.
"""

import socket
from unittest.mock import patch

import pytest

from scanner.core import scan_port, scan_ports


class TestScanPort:
    """Test unitari per scan_port()."""

    def test_returns_true_when_connection_succeeds(self):
        """La porta è aperta quando create_connection non solleva eccezioni."""
        with patch("scanner.core.socket.create_connection"):
            assert scan_port("127.0.0.1", 80) is True

    def test_returns_false_on_connection_refused(self):
        """La porta è chiusa quando il sistema operativo invia RST (ConnectionRefusedError)."""
        with patch(
            "scanner.core.socket.create_connection",
            side_effect=ConnectionRefusedError,
        ):
            assert scan_port("127.0.0.1", 9999) is False

    def test_returns_false_on_timeout(self):
        """La porta è filtrata quando la connessione va in timeout."""
        with patch(
            "scanner.core.socket.create_connection",
            side_effect=socket.timeout,
        ):
            assert scan_port("127.0.0.1", 9999) is False

    def test_returns_false_on_os_error(self):
        """La porta è irraggiungibile in caso di errori di rete generici del SO."""
        with patch(
            "scanner.core.socket.create_connection",
            side_effect=OSError("Network unreachable"),
        ):
            assert scan_port("192.0.2.1", 80) is False

    def test_uses_provided_timeout(self):
        """scan_port passa l'argomento timeout a create_connection."""
        with patch("scanner.core.socket.create_connection") as mock_conn:
            scan_port("127.0.0.1", 80, timeout=2.5)
        mock_conn.assert_called_once_with(("127.0.0.1", 80), timeout=2.5)


class TestScanPorts:
    """Test unitari per scan_ports()."""

    def test_returns_result_for_every_port(self):
        """Il dizionario risultato contiene esattamente le porte richieste."""
        ports = [22, 80, 443]
        with patch("scanner.core.scan_port", return_value=False):
            results = scan_ports("127.0.0.1", ports)
        assert set(results.keys()) == set(ports)

    def test_open_port_marked_true(self):
        """Solo la porta la cui probe ha successo viene marcata come aperta."""
        def _mock_scan(host: str, port: int, timeout: float = 1.0) -> bool:
            return port == 80

        with patch("scanner.core.scan_port", side_effect=_mock_scan):
            results = scan_ports("127.0.0.1", [22, 80, 443])

        assert results[80] is True
        assert results[22] is False
        assert results[443] is False

    def test_all_closed_when_all_fail(self):
        """Tutte le porte sono False quando ogni connessione viene rifiutata."""
        ports = list(range(1, 11))
        with patch("scanner.core.scan_port", return_value=False):
            results = scan_ports("127.0.0.1", ports)
        assert all(not v for v in results.values())

    def test_progress_callback_called_for_each_port(self):
        """progress_callback viene invocato una volta per porta con (porta, stato)."""
        ports = [22, 80]
        seen: list[tuple[int, bool]] = []

        with patch("scanner.core.scan_port", return_value=True):
            scan_ports(
                "127.0.0.1",
                ports,
                progress_callback=lambda p, s: seen.append((p, s)),
            )

        assert sorted(p for p, _ in seen) == sorted(ports)

    def test_empty_port_list_returns_empty_dict(self):
        """Scansionare una lista vuota produce un dizionario vuoto senza errori."""
        results = scan_ports("127.0.0.1", [])
        assert results == {}
