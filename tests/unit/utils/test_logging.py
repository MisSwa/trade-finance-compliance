import pytest
from app.utils.logging import mask_sensitive_field


@pytest.mark.unit
def test_mask_returns_hash_format():
    result = mask_sensitive_field("SomeValue")
    assert result.startswith("[ENTITY:")
    assert result.endswith("]")


@pytest.mark.unit
def test_mask_is_deterministic():
    value = "Zarkon Trading Corporation"
    assert mask_sensitive_field(value) == mask_sensitive_field(value)


@pytest.mark.unit
def test_mask_does_not_contain_original_value():
    value = "Zarkon Trading Corporation"
    result = mask_sensitive_field(value)
    assert value not in result
    assert "Zarkon" not in result


@pytest.mark.unit
def test_different_values_produce_different_hashes():
    assert mask_sensitive_field("ValueA") != mask_sensitive_field("ValueB")


@pytest.mark.unit
def test_mask_output_length_is_consistent():
    # [ENTITY: + 8 hex chars + ]  = 17 chars
    result = mask_sensitive_field("anything")
    assert len(result) == 17
