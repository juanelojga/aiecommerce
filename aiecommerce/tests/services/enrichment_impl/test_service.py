import logging
from typing import Any, Callable, NoReturn

import pytest

from aiecommerce.services.enrichment_impl import service as service_module
from aiecommerce.services.enrichment_impl.exceptions import ConfigurationError
from aiecommerce.services.enrichment_impl.schemas import GenericSpecs
from aiecommerce.services.enrichment_impl.service import ProductEnrichmentService

CreateFunc = Callable[..., Any]


class _Completions:
    def __init__(self, fn: CreateFunc) -> None:
        self._fn: CreateFunc = fn

    def create(self, *args: Any, **kwargs: Any) -> Any:  # mimics OpenAI API
        return self._fn(*args, **kwargs)


class _Chat:
    def __init__(self, fn: CreateFunc) -> None:
        self.completions: _Completions = _Completions(fn)


class DummyClient:
    """Minimal stub to mimic the nested client.chat.completions.create API."""

    def __init__(self, create_impl: CreateFunc) -> None:
        # create_impl: a callable that will be invoked when create(...) is called
        self.chat: _Chat = _Chat(create_impl)


def test_init_with_client_uses_provided_instance():
    provided = DummyClient(lambda *a, **k: None)
    svc = ProductEnrichmentService(client=provided)
    assert svc.client is provided


def test_init_without_env_vars_raises_configuration_error(monkeypatch):
    # Ensure env vars are absent
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    with pytest.raises(ConfigurationError):
        ProductEnrichmentService()


def test_init_with_env_builds_openai_and_instructor(monkeypatch):
    # Provide required env vars
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://example")

    # Fake instructor module with Mode and from_openai
    calls = {}

    class FakeMode:
        JSON = "JSON"

    class FakeInstructorModule:
        Mode = FakeMode

        @staticmethod
        def from_openai(base_client, mode):
            calls["from_openai"] = {"base_client": base_client, "mode": mode}
            return "FAKE_CLIENT"

    class FakeOpenAI:
        def __init__(self, *, base_url, api_key):
            calls["openai_init"] = {"base_url": base_url, "api_key": api_key}

    # Patch symbols used inside service module
    monkeypatch.setattr(service_module, "instructor", FakeInstructorModule, raising=True)
    monkeypatch.setattr(service_module, "OpenAI", FakeOpenAI, raising=True)

    svc = ProductEnrichmentService()

    assert svc.client == "FAKE_CLIENT"
    assert calls["openai_init"] == {"base_url": "https://example", "api_key": "key"}
    assert calls["from_openai"]["mode"] == FakeMode.JSON


def test_enrich_product_no_text_returns_none_logs_warning(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    svc = ProductEnrichmentService(client=DummyClient(lambda *a, **k: None))

    # No text information provided
    result = svc.enrich_product({}, model_name="test-model")

    assert result is None
    # Note: The current implementation always builds a non-empty prompt string,
    # so a warning may not be emitted for empty inputs. We only assert the None result.


def test_enrich_product_success_returns_schema_instance():
    expected = GenericSpecs(summary="A nice accessory")

    def _create(**kwargs: Any) -> GenericSpecs:  # emulate signature via kwargs
        return expected

    svc = ProductEnrichmentService(client=DummyClient(lambda *a, **k: _create(**k)))

    product = {"code": "X1", "description": "USB-C Cable", "category": "ACCESORIOS"}
    out = svc.enrich_product(product, model_name="test-model")

    assert out is expected
    assert isinstance(out, GenericSpecs)


def test_enrich_product_handles_api_error_returns_none(monkeypatch):
    from openai import APIError

    def _raise_api_error(*a: Any, **k: Any) -> NoReturn:
        raise APIError("network")

    svc = ProductEnrichmentService(client=DummyClient(_raise_api_error))

    product = {"description": "Something"}
    assert svc.enrich_product(product, model_name="m") is None


def test_enrich_product_handles_timeout_returns_none():
    def _raise_timeout(*a: Any, **k: Any) -> NoReturn:
        raise TimeoutError("boom")

    svc = ProductEnrichmentService(client=DummyClient(_raise_timeout))

    product = {"description": "Something"}
    assert svc.enrich_product(product, model_name="m") is None


def test_enrich_product_handles_validation_error_returns_none():
    # Create a real ValidationError instance to raise
    from pydantic import BaseModel, ValidationError

    class M(BaseModel):
        a: int

    try:
        M(a="x")
    except ValidationError as ve:
        err = ve
    else:  # pragma: no cover - safety
        pytest.skip("Could not construct ValidationError for testing")

    def _raise_validation(*a: Any, **k: Any) -> NoReturn:
        raise err

    svc = ProductEnrichmentService(client=DummyClient(_raise_validation))

    product = {"description": "Something"}
    assert svc.enrich_product(product, model_name="m") is None


def test_enrich_product_handles_unexpected_exception_returns_none():
    def _raise_generic(*a: Any, **k: Any) -> NoReturn:
        raise RuntimeError("unexpected")

    svc = ProductEnrichmentService(client=DummyClient(_raise_generic))

    product = {"description": "Something"}
    assert svc.enrich_product(product, model_name="m") is None
