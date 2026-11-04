"""OpenAPI documentation for SMS testing and cookie authentication."""

from django.conf import settings
from django.http import HttpResponse, JsonResponse


def schema(_request):
    def body(properties, required):
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }
                }
            },
        }

    string = {"type": "string"}
    protected = [{"cookieAuth": []}, {"bearerAuth": []}]
    document = {
        "openapi": "3.0.3",
        "info": {
            "title": "Riana SMS API",
            "version": "1.0.0",
            "description": (
                "Execute POST /api/auth/login with your care account first. The browser "
                "stores the HttpOnly login cookie and sends it with SMS invitations. "
                "Alternatively use Authorize with an existing application JWT. "
                "Do not enter an Africa's Talking API key here. SMS charges apply. "
                "Inbound testing creates real feedback records."
            ),
        },
        "servers": [{"url": "/"}],
        "components": {
            "securitySchemes": {
                "cookieAuth": {"type": "apiKey", "in": "cookie", "name": settings.JWT_COOKIE_NAME},
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            }
        },
        "paths": {
            "/api/auth/login": {
                "post": {
                    "tags": ["Authentication"],
                    "summary": "Sign in before testing SMS",
                    "requestBody": body(
                        {
                            "identifier": {**string, "example": "care"},
                            "password": {**string, "format": "password"},
                        },
                        ["identifier", "password"],
                    ),
                    "responses": {
                        "200": {"description": "Signed in; HttpOnly cookie set"},
                        "401": {"description": "Invalid credentials"},
                    },
                }
            },
            "/api/auth/me": {
                "get": {
                    "tags": ["Authentication"],
                    "summary": "Check current login",
                    "security": protected,
                    "responses": {
                        "200": {"description": "Current user"},
                        "403": {"description": "Sign in first"},
                    },
                }
            },
            "/api/auth/logout": {
                "post": {
                    "tags": ["Authentication"],
                    "summary": "Sign out",
                    "responses": {"200": {"description": "Login cookie cleared"}},
                }
            },
            "/api/sms/invite": {
                "post": {
                    "tags": ["SMS"],
                    "summary": "Send a survey invitation",
                    "security": protected,
                    "description": (
                        "Inspect result.status and recipient statuses. "
                        "HTTP 200 and ok alone do not confirm acceptance or delivery."
                    ),
                    "requestBody": body(
                        {
                            "phone": {
                                **string,
                                "description": "International number including + and country code",
                            },
                            "name": {**string, "maxLength": 160},
                        },
                        ["phone"],
                    ),
                    "responses": {
                        "200": {
                            "description": "Provider result; inspect recipient status",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {"type": "boolean"},
                                            "result": {
                                                "type": "object",
                                                "additionalProperties": True,
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "400": {"description": "Invalid input"},
                        "403": {"description": "Sign in first"},
                    },
                }
            },
            "/api/sms/africastalking/send": {
                "post": {
                    "tags": ["Africa's Talking live SMS"],
                    "summary": "Send a live SMS through Africa's Talking",
                    "security": protected,
                    "description": (
                        "Staff-only provider-specific endpoint. It always uses the live "
                        "Africa's Talking API, regardless of SMS_PROVIDER, and rejects "
                        "sandbox or missing credentials. SMS charges may apply. A 200 "
                        "response means the provider accepted the request, not that the "
                        "handset received the SMS."
                    ),
                    "requestBody": body(
                        {
                            "phone": {
                                **string,
                                "pattern": r"^\+[1-9]\d{7,14}$",
                                "example": "+254700000000",
                                "description": "International number in E.164 format.",
                            },
                            "message": {
                                **string,
                                "maxLength": 320,
                                "example": "Thanks for buying our paint! Reply 4 5 4 to rate us.",
                            },
                        },
                        ["phone", "message"],
                    ),
                    "responses": {
                        "200": {
                            "description": (
                                "Accepted by Africa's Talking; delivery is not confirmed."
                            ),
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "accepted"},
                                            "provider": {
                                                "type": "string",
                                                "example": "africastalking",
                                            },
                                            "detail": {"type": "string"},
                                            "recipients": {
                                                "type": "array",
                                                "items": {"type": "object"},
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "400": {"description": "Invalid phone number or message."},
                        "403": {"description": "Sign in as a staff user."},
                        "502": {
                            "description": (
                                "Africa's Talking rejected the request or could not be reached."
                            )
                        },
                        "503": {
                            "description": (
                                "Live credentials are missing or sandbox mode is configured."
                            )
                        },
                    },
                }
            },
            "/api/sms/inbound": {
                "post": {
                    "tags": ["SMS"],
                    "summary": "Receive a customer rating reply",
                    "description": (
                        "Provider callback. Executing this creates feedback. "
                        "Currently publicly accessible without webhook authentication."
                    ),
                    "requestBody": body(
                        {"from": string, "text": {**string, "example": "4 5 4"}}, ["from", "text"]
                    ),
                    "responses": {
                        "200": {"description": "Rating processed or invalid reply reported"}
                    },
                }
            },
        },
    }
    document["paths"]["/api/sms/gateway/status"] = {
        "get": {
            "tags": ["Android SIM gateway"],
            "summary": "Check gateway configuration",
            "security": protected,
            "responses": {
                "200": {"description": "Provider and configuration flags; no credentials"},
                "403": {"description": "Sign in first"},
            },
        }
    }
    document["paths"]["/api/sms/gateway/inbound"] = {
        "post": {
            "tags": ["Android SIM gateway"],
            "summary": "Receive a signed Android SMS reply",
            "description": (
                "SMSGate signs the exact raw JSON body followed by X-Timestamp "
                "using HMAC-SHA256. The signature must match the exact request bytes. "
                "Unsigned Swagger requests are intentionally rejected."
            ),
            "parameters": [
                {"in": "header", "name": name, "required": True, "schema": string}
                for name in ["X-Timestamp", "X-Signature"]
            ],
            "requestBody": body(
                {
                    "id": string,
                    "deviceId": string,
                    "event": {**string, "enum": ["sms:received"]},
                    "payload": {
                        "type": "object",
                        "required": ["sender", "message"],
                        "properties": {
                            "sender": string,
                            "message": {**string, "example": "4 5 4"},
                        },
                    },
                },
                ["id", "deviceId", "event", "payload"],
            ),
            "responses": {
                "200": {"description": "Reply processed, ignored, or duplicate"},
                "400": {"description": "Invalid event"},
                "403": {"description": "Invalid signature, timestamp, or device"},
            },
        }
    }
    response = JsonResponse(document)
    response["Cache-Control"] = "no-store"
    return response


def swagger(_request):
    return HttpResponse("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Riana SMS API — Swagger</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head><body><div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: "/api/schema/", dom_id: "#swagger-ui", withCredentials: true,
persistAuthorization: false, validatorUrl: null, supportedSubmitMethods: ["get", "post"]});</script>
</body></html>""")
