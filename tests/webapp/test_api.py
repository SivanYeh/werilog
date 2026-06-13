from fastapi.testclient import TestClient
from werilog.webapp.server import app

client = TestClient(app)

def test_parse_api():
    response = client.post("/api/parse", json={"code": "module test(); endmodule", "positions": {}})
    assert response.status_code == 200
    data = response.json()
    assert "layout" in data
    assert "errors" in data

def test_suggest_api():
    response = client.post("/api/suggest", json={"prefix": "module test(", "errors": []})
    assert response.status_code == 200
    data = response.json()
    assert "suggestion" in data
