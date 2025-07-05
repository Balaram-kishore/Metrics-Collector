from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class MetricsPayload(BaseModel):
    hostname: str
    metrics: dict

@app.post("/ingest")
async def ingest(metrics: MetricsPayload):
    print(f"Received metrics from {metrics.hostname}: {metrics.metrics}")
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)