from app.config import settings
from app.schemas import InterpretIn
from app.services import interpretation


def test_malformed_local_model_response_falls_back_to_rules(monkeypatch):
    class MalformedResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "[1]"}

    monkeypatch.setattr(settings, "ollama_url", "http://localhost:11434")
    monkeypatch.setattr(interpretation.httpx, "post", lambda *args, **kwargs: MalformedResponse())
    result = interpretation.interpret(InterpretIn(text="I have 60 meals available tonight"))
    assert result["provider"] == "rule_based"
    assert result["category"] == "FOOD"
    assert result["quantity"] == 60
