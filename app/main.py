from fastapi import FastAPI

app = FastAPI(
    title="access-sentinel",
    description="Simulated patient-records access system exploring resilience vs. strict access control.",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "access-sentinel"}
