from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Public health-check endpoint for liveness probes and load balancers.

    Overrides global auth/permission defaults intentionally — this endpoint
    must remain accessible without an API key or IP whitelist so that Docker
    HEALTHCHECK, Railway, and other infrastructure probes can reach it.
    """

    authentication_classes: list[type] = []  # No auth required (public endpoint)
    permission_classes = [AllowAny]  # No IP whitelist check

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})
