from fastapi.testclient import TestClient

from app.main import app


def test_swagger_and_openapi_document_primary_api_contracts():
    with TestClient(app) as client:
        docs_response = client.get("/docs")
        spec_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert "swagger-ui" in docs_response.text
    assert spec_response.status_code == 200

    spec = spec_response.json()
    assert spec["info"]["title"] == "AI Vacation Planner"
    assert spec["info"]["version"] == "1.0.0"
    assert {
        "/auth/register",
        "/auth/login",
        "/trips",
        "/trips/{trip_id}",
        "/itineraries",
        "/itineraries/generate",
        "/itineraries/{trip_id}",
        "/kb/query",
    }.issubset(spec["paths"])

    generate_operation = spec["paths"]["/itineraries/generate"]["post"]
    assert generate_operation["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ItineraryGenerateAI")
    assert generate_operation["responses"]["201"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/ItineraryResponse")

    operation_ids = [
        operation["operationId"]
        for path_item in spec["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert len(operation_ids) == len(set(operation_ids))
