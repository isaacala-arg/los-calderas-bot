from src.brain import ganchos


def test_howto_incluye_familias_educativas():
    block = ganchos.build_ganchos_block("howto")
    assert "principiantes" in block
    assert "hacks" in block
    assert "choque_real" not in block  # es para trend/tech/fsd


def test_trend_prioriza_choque_real():
    block = ganchos.build_ganchos_block("trend")
    assert "choque_real" in block
    assert "PRIORIDAD ALTA" in block


def test_incluye_reglas_de_rotacion_y_ctas():
    block = ganchos.build_ganchos_block("lifestyle")
    assert "misma familia dos veces seguidas" in block
    assert "CTA" in block
    assert "sígueme" in block  # la regla de nunca decirlo literal
    assert "2-3 segundos" in block


def test_tipo_desconocido_usa_instantaneo():
    block = ganchos.build_ganchos_block("loquesea")
    assert "instantaneo" in block
