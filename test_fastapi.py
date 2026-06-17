from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from typing import Optional, List

app = FastAPI()

@app.get("/test")
def test_endpoint(
    agrupadores: Optional[List[str]] = Query(None)
):
    return {"agrupadores": agrupadores}

client = TestClient(app)
res = client.get("/test?agrupadores=clientes&agrupadores=credito")
print("Response:", res.json())
