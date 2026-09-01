from fastapi import FastAPI

app = FastAPI(title="Baobab Freight Assistant API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
