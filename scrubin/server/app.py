from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .routes import router
from .error_models import SessionNotFoundError, ValidationError, PersistenceError, AuthorizationError

app = FastAPI(title="Scrubin Core HTTP API (Phase P.3)")
app.include_router(router)
app.include_router(router, prefix="/api/v1")

# Dashboard API – read‑only visualization and inspection.
from scrubin.dashboard.routes import router as dashboard_router
from scrubin.experiments.routes import router as experiments_router
from scrubin.planner.routes import router as planner_router
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(experiments_router, prefix="/dashboard")
app.include_router(planner_router, prefix="/dashboard")
from scrubin.search.routes import router as search_router
app.include_router(search_router, prefix="/dashboard")

from scrubin.optimization.routes import router as optimization_router
app.include_router(optimization_router, prefix="/dashboard")

# Global exception handlers – map immutable error models to HTTP responses.
@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
    return JSONResponse(status_code=404, content=jsonable_encoder(exc))

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content=jsonable_encoder(exc))

@app.exception_handler(PersistenceError)
async def persistence_error_handler(request: Request, exc: PersistenceError):
    return JSONResponse(status_code=500, content=jsonable_encoder(exc))

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(status_code=exc.code or 403, content=jsonable_encoder(exc))
