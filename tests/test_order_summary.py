import asyncio
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.integrations import mock_services
from app.integrations.retry import TransientServiceError
from app.main import app
from app.modules.orders import service

client = TestClient(app)


def configurar_teste(monkeypatch: pytest.MonkeyPatch, timeout=0.01) -> None:
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: Settings(request_timeout=timeout, max_attempts=3, backoff_base=0),
    )


def test_consulta_completa() -> None:
    response = client.get("/orders/12345/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["services"] == {
        "cliente": "success", "estoque": "success", "financeiro": "success"
    }
    assert not body["warnings"]


def test_timeout_financeiro_preserva_outros(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_teste(monkeypatch)
    tentativas = 0

    async def resposta_rapida(order_id: str) -> dict:
        return {"pedido": order_id}

    async def financeiro_lento(order_id: str) -> dict:
        nonlocal tentativas
        tentativas += 1
        await asyncio.sleep(0.1)
        return {"situacao": "regular"}

    monkeypatch.setattr(mock_services, "consultar_cliente", resposta_rapida)
    monkeypatch.setattr(mock_services, "consultar_estoque", resposta_rapida)
    monkeypatch.setattr(mock_services, "consultar_financeiro", financeiro_lento)
    response = client.get("/orders/12345/summary")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "partial"
    assert body["services"] == {
        "cliente": "success", "estoque": "success", "financeiro": "timeout"
    }
    assert body["data"]["cliente"] is not None
    assert body["data"]["estoque"] is not None
    assert body["data"]["financeiro"] is None
    assert [w["service"] for w in body["warnings"]] == ["financeiro"]
    assert tentativas == 3


def test_recuperacao_apos_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_teste(monkeypatch, timeout=2)
    tentativas = 0

    async def financeiro_instavel(order_id: str) -> dict:
        nonlocal tentativas
        tentativas += 1
        if tentativas == 1:
            raise TransientServiceError("Falha temporária")
        return {"situacao": "regular"}

    monkeypatch.setattr(mock_services, "consultar_financeiro", financeiro_instavel)
    response = client.get("/orders/12345/summary")
    assert response.status_code == 200
    assert response.json()["status"] == "complete"
    assert tentativas == 2


def test_falha_apos_tres_tentativas(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_teste(monkeypatch, timeout=2)
    tentativas = 0

    async def financeiro_indisponivel(order_id: str) -> dict:
        nonlocal tentativas
        tentativas += 1
        raise TransientServiceError("Serviço indisponível")

    monkeypatch.setattr(mock_services, "consultar_financeiro", financeiro_indisponivel)
    response = client.get("/orders/12345/summary")
    body = response.json()
    assert body["status"] == "partial"
    assert body["services"]["financeiro"] == "error"
    assert body["data"]["cliente"] is not None
    assert body["data"]["estoque"] is not None
    assert tentativas == 3


def test_erro_permanente_nao_gera_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_teste(monkeypatch, timeout=2)
    tentativas = 0

    async def financeiro_invalido(order_id: str) -> dict:
        nonlocal tentativas
        tentativas += 1
        raise ValueError("Requisição inválida")

    monkeypatch.setattr(mock_services, "consultar_financeiro", financeiro_invalido)
    body = client.get("/orders/12345/summary").json()
    assert body["services"]["financeiro"] == "error"
    assert tentativas == 1


def test_integracoes_iniciam_concorrentemente(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_teste(monkeypatch, timeout=1)
    total_iniciadas = 0
    todas_iniciadas = asyncio.Event()

    async def aguardar_outras(order_id: str) -> dict:
        nonlocal total_iniciadas
        total_iniciadas += 1
        if total_iniciadas == 3:
            todas_iniciadas.set()
        await todas_iniciadas.wait()
        return {"pedido": order_id}

    monkeypatch.setattr(mock_services, "consultar_cliente", aguardar_outras)
    monkeypatch.setattr(mock_services, "consultar_estoque", aguardar_outras)
    monkeypatch.setattr(mock_services, "consultar_financeiro", aguardar_outras)
    body = client.get("/orders/12345/summary").json()
    assert body["status"] == "complete"
    assert total_iniciadas == 3


def test_configuracao_invalida() -> None:
    with pytest.raises(ValueError):
        Settings(request_timeout=0)
    with pytest.raises(ValueError):
        Settings(max_attempts=4)
    with pytest.raises(ValueError):
        Settings(backoff_base=-1)
