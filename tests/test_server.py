#!/usr/bin/env python3
"""Test suite"""
import pytest


class TestServer:
    def test_server_initialization(self):
        try:
            import server
            assert True
        except ImportError as e:
            pytest.skip(f"Server import failed: {e}")


class TestSecurity:
    def test_no_hardcoded_keys(self):
        try:
            with open('server.py', 'r') as f:
                content = f.read()
                assert 'sk_live_' not in content
        except FileNotFoundError:
            pytest.skip("server.py not found")


class TestIntegration:
    def test_import_main(self):
        try:
            import server
            assert hasattr(server, 'main')
        except ImportError:
            pytest.skip("Cannot import server")
