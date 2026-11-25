"""Cas de vérification V1 à V16 de la SPEC §12.1.

Les cas sont ajoutés ici au fur et à mesure des étapes (Calculs, API).
Socle : V8.
"""

import pytest

import config
import main
from config import ConfigError


def test_v08_info_weight_equal_to_tech_weight_refuses_to_start(monkeypatch):
    """V8 : poids Informations égal au poids Graphique → l'application refuse de démarrer."""
    monkeypatch.setattr(
        config, "POIDS", {"infos": 0.30, "tech": 0.30, "ratios": 0.30, "hasard": 0.10}
    )
    with pytest.raises(ConfigError, match="RG-04"):
        main.create_app()
