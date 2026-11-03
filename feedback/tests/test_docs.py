"""Keep the interactive SMS documentation aligned with the protected API."""

from django.test import Client


def test_sms_schema_documents_authentication_and_request_fields():
    document = Client().get("/api/schema/").json()
    assert document["servers"] == [{"url": "/"}]
    invite = document["paths"]["/api/sms/invite"]["post"]
    assert invite["security"] == [{"cookieAuth": []}, {"bearerAuth": []}]
    request = invite["requestBody"]["content"]["application/json"]["schema"]
    assert request["required"] == ["phone"]
    assert set(request["properties"]) == {"phone", "name"}
    assert "/api/auth/login" in document["paths"]


def test_swagger_loads_same_origin_schema_with_cookie_support():
    response = Client().get("/api/docs/")
    assert response.status_code == 200
    assert b'url: "/api/schema/"' in response.content
    assert b"withCredentials: true" in response.content


def test_swagger_does_not_make_invite_public():
    response = Client().post("/api/sms/invite", {"phone": "+254700000000"})
    assert response.status_code == 403
