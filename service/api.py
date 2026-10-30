"""Local-only FastAPI service. Start on 127.0.0.1, not a public interface."""
import os
import threading
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field
from .semantic import ROOT, catalog, query_metrics
from .agent import AgentError, investigate

app = FastAPI(title='Voltwise analytics and local agent', docs_url='/api/docs')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])
lock = threading.Lock()

class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=1500)

@app.get('/api/status')
def status():
    return {'mode': 'local', 'model_configured': bool(os.environ.get('VOLTWISE_OLLAMA_MODEL')),
            'model': os.environ.get('VOLTWISE_OLLAMA_MODEL'),
            'note': 'Configuration does not establish model availability.'}

@app.get('/api/catalog')
def metrics_catalog():
    return catalog()

@app.get('/api/metrics/{metric}')
def metric(metric: str, cell: str = '__all__'):
    try:
        return query_metrics([metric], cell)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/agent')
def agent(body: Question, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Use the local Voltwise page to query this local service.')
    if not lock.acquire(blocking=False):
        raise HTTPException(429, 'One investigation is already running.')
    try:
        return investigate(body.question)
    except AgentError as exc:
        raise HTTPException(503, str(exc)) from exc
    finally:
        lock.release()

app.mount('/', StaticFiles(directory=ROOT/'docs', html=True), name='dashboard')
