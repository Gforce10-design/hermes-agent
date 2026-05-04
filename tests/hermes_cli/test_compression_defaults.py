from __future__ import annotations


def test_default_compression_threshold_is_80_percent():
    from hermes_cli.config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["compression"]["threshold"] == 0.80


def test_cli_local_default_compression_threshold_is_80_percent():
    import importlib
    import cli

    cli_mod = importlib.reload(cli)
    cfg = cli_mod.load_cli_config()
    assert cfg["compression"]["threshold"] == 0.80
