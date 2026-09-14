"""Tests for network.validation."""

from network.validation import (
    validate_ip,
    validate_port
)


def test_validate_ip_valid():

    assert validate_ip("127.0.0.1") is True
    assert validate_ip("192.168.1.10") is True
    assert validate_ip("8.8.8.8") is True


def test_validate_ip_reserved_zero():

    assert validate_ip("0.0.0.0") is False


def test_validate_ip_reserved_broadcast():

    assert validate_ip("255.255.255.255") is False


def test_validate_ip_invalid_format():

    assert validate_ip("999.999.999.999") is False
    assert validate_ip("abc") is False
    assert validate_ip("") is False


def test_validate_port_valid():

    assert validate_port("1") is True
    assert validate_port("80") is True
    assert validate_port("65535") is True


def test_validate_port_not_digit():

    assert validate_port("abc") is False
    assert validate_port("80a") is False
    assert validate_port("") is False


def test_validate_port_too_small():

    assert validate_port("0") is False


def test_validate_port_too_large():

    assert validate_port("65536") is False  