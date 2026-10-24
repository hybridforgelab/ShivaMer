from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from converter import to_mermaid

app = FastAPI(title="ShivaMer API")

DEFAULT_ORIGINS = "https://shivamer.hybridforgelab.com,http://localhost:5173,http://localhost:8080"

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class ConvertReq(BaseModel):
    code: str = Field(min_length=1, max_length=20_000)

class ConvertResp(BaseModel):
    mermaid: str

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/")
def root():
    return {"message": "ShivaMer API. Use /convert (POST) or /docs."}

@app.post("/convert", response_model=ConvertResp)
def convert(req: ConvertReq):
    try:
        return ConvertResp(mermaid=to_mermaid(req.code))
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"SyntaxError: {e.msg} (line {e.lineno})") from e
    except (RecursionError, MemoryError):
        raise HTTPException(status_code=400, detail="Code is too deeply nested to convert.") from None
