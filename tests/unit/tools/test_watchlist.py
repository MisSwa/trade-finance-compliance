import pytest
from app.tools.watchlist import (
    check_entity,
    check_vessel,
    check_country,
    check_port,
    check_goods,
)


@pytest.mark.unit
def test_known_sanctioned_entity_returns_hit():
    result = check_entity("Zarkon Trading Corporation")
    assert result["hit"] is True
    assert result["severity"] in ("critical", "high", "medium")
    assert result["match"] is not None


@pytest.mark.unit
def test_unknown_entity_returns_no_hit():
    result = check_entity("Legitimate Imports Ltd")
    assert result["hit"] is False
    assert result["match"] is None
    assert result["severity"] == "none"


@pytest.mark.unit
def test_entity_check_is_case_insensitive():
    assert check_entity("zarkon trading corporation")["hit"] is True
    assert check_entity("ZARKON TRADING CORPORATION")["hit"] is True
    assert check_entity("Zarkon Trading Corporation")["hit"] is True


@pytest.mark.unit
def test_critical_entity_returns_critical_severity():
    result = check_entity("Pacific Rim Commodities Ltd")
    assert result["hit"] is True
    assert result["severity"] == "critical"


@pytest.mark.unit
def test_known_sanctioned_vessel_returns_hit():
    result = check_vessel("MV Phantom Star")
    assert result["hit"] is True
    assert result["severity"] == "critical"


@pytest.mark.unit
def test_unknown_vessel_returns_no_hit():
    result = check_vessel("MV Clean Carrier")
    assert result["hit"] is False


@pytest.mark.unit
def test_high_risk_country_returns_hit():
    result = check_country("Ruritania")
    assert result["hit"] is True
    assert result["severity"] == "high"


@pytest.mark.unit
def test_safe_country_returns_no_hit():
    result = check_country("Germany")
    assert result["hit"] is False


@pytest.mark.unit
def test_country_check_is_case_insensitive():
    assert check_country("ruritania")["hit"] is True
    assert check_country("RURITANIA")["hit"] is True


@pytest.mark.unit
def test_high_risk_port_returns_hit():
    result = check_port("Port Obscura")
    assert result["hit"] is True


@pytest.mark.unit
def test_safe_port_returns_no_hit():
    result = check_port("Port of Hamburg")
    assert result["hit"] is False


@pytest.mark.unit
def test_prohibited_goods_keyword_returns_hit():
    result = check_goods("shipment of dual-use electronics for industrial use")
    assert result["hit"] is True
    assert result["severity"] == "critical"
    assert result["match"] == "dual-use electronics"


@pytest.mark.unit
def test_safe_goods_returns_no_hit():
    result = check_goods("cotton textiles and garments")
    assert result["hit"] is False
