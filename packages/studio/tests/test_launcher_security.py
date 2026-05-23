"""Tests for the raptor_studio.py launcher guardrails."""

from __future__ import annotations

import pytest

import raptor_studio


def test_loopback_hosts_do_not_need_remote_override():
    for host in ("127.0.0.1", "localhost", "::1"):
        raptor_studio._validate_bind_host(host, allow_remote=False)


def test_non_loopback_host_requires_remote_override():
    with pytest.raises(SystemExit):
        raptor_studio._validate_bind_host("0.0.0.0", allow_remote=False)


def test_non_loopback_host_allowed_with_explicit_override(capsys):
    raptor_studio._validate_bind_host("0.0.0.0", allow_remote=True)
    assert "WARNING: RAPTOR Studio" in capsys.readouterr().err
