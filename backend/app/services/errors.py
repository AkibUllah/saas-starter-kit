from __future__ import annotations


class ServiceError(Exception):
    """Domain error carrying an HTTP status and a stable machine-readable code."""

    status_code = 400
    code = "bad_request"

    def __init__(
        self, detail: str, *, status_code: int | None = None, code: str | None = None
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFound(ServiceError):
    status_code = 404
    code = "not_found"


class Unauthorized(ServiceError):
    status_code = 401
    code = "unauthorized"


class Forbidden(ServiceError):
    status_code = 403
    code = "forbidden"


class Conflict(ServiceError):
    status_code = 409
    code = "conflict"


class Locked(ServiceError):
    status_code = 423
    code = "locked"


class PlanLimit(ServiceError):
    status_code = 402
    code = "plan_limit_reached"
