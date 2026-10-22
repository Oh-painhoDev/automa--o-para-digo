import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from core.manager import AutomationManager

app = FastAPI(title="Conecta System // Multi-Account Automation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = AutomationManager()

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class ImportPayload(BaseModel):
    tokens: str
    proxies: str
    links: str
    comments: Optional[str] = None

class ProxyPayload(BaseModel):
    proxies: str

class SettingsPayload(BaseModel):
    min_education_likes: Optional[int] = 3
    max_education_likes: Optional[int] = 6
    min_action_delay: Optional[float] = 3.0
    max_action_delay: Optional[float] = 7.0
    like_probability_min: Optional[float] = 0.40
    like_probability_max: Optional[float] = 0.45

class AutoLikePayload(BaseModel):
    keywords: List[str]
    count: Optional[int] = 15

class VideoDownloadPayload(BaseModel):
    url_or_id: str

@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Interface Web não encontrada</h1>"

@app.get("/api/status")
async def get_status():
    summary = manager.get_summary()
    summary["logs"] = manager.logs[-50:]
    return summary

@app.post("/api/import")
async def import_data(payload: ImportPayload):
    manager.import_data(
        raw_tokens=payload.tokens,
        raw_proxies=payload.proxies,
        raw_links=payload.links,
        raw_comments=payload.comments
    )
    groups = {account.group for account in manager.accounts}
    return {
        "success": True,
        "message": f"{len(manager.accounts)} contas pareadas com sucesso em {len(groups)} grupo(s) (1 conta : 1 proxy : 1 link)."
    }

@app.post("/api/proxies")
async def update_proxies(payload: ProxyPayload):
    if not manager.accounts:
        return {"success": False, "message": "Importe as contas primeiro para aplicar os proxies."}

    proxy_count = manager.update_proxies(payload.proxies)
    account_count = len(manager.accounts)
    if proxy_count > account_count:
        message = f"{proxy_count} proxies recebidos; os {account_count} primeiros foram aplicados às contas."
    elif proxy_count < account_count:
        message = f"{proxy_count} proxies aplicados; {account_count - proxy_count} conta(s) ficaram sem proxy."
    else:
        message = f"{proxy_count} proxies aplicados com sucesso, um por conta."

    return {"success": True, "message": message}

@app.post("/api/start")
async def start_automation():
    if not manager.accounts:
        return {"success": False, "message": "Nenhuma conta importada. Importe contas primeiro."}
    asyncio.create_task(manager.start())
    return {"success": True, "message": "Ciclo completo de automação iniciado."}

@app.post("/api/stop")
async def stop_automation():
    await manager.stop()
    return {"success": True, "message": "Operação pausada com sucesso."}

@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    if payload.min_education_likes is not None:
        manager.config.min_education_likes = payload.min_education_likes
    if payload.max_education_likes is not None:
        manager.config.max_education_likes = payload.max_education_likes
    if payload.min_action_delay is not None:
        manager.config.min_action_delay = payload.min_action_delay
    if payload.max_action_delay is not None:
        manager.config.max_action_delay = payload.max_action_delay
    if payload.like_probability_min is not None:
        manager.config.like_probability_min = payload.like_probability_min
    if payload.like_probability_max is not None:
        manager.config.like_probability_max = payload.like_probability_max
    return {"success": True, "message": "Configurações salvas."}

# Batch automation triggers
@app.post("/api/actions/unfollow-non-followers")
async def action_unfollow_non_followers():
    if not manager.accounts:
        return {"success": False, "message": "Importe contas primeiro."}
    asyncio.create_task(manager.run_unfollow_non_followers_batch())
    return {"success": True, "message": f"Remoção de quem não segue de volta iniciada em {len(manager.accounts)} contas."}

@app.post("/api/actions/auto-like")
async def action_auto_like(payload: AutoLikePayload):
    if not manager.accounts:
        return {"success": False, "message": "Importe contas primeiro."}
    asyncio.create_task(manager.run_auto_liker_batch(payload.keywords, payload.count or 15))
    return {"success": True, "message": f"Curtidor automático ativado para {payload.keywords}."}

@app.post("/api/actions/video-download")
async def action_video_download(payload: VideoDownloadPayload):
    videos = await manager.get_video_stream(payload.url_or_id)
    if not videos:
        return {"success": False, "message": "Nenhum vídeo MP4 encontrado para esse Tweet."}
    return {"success": True, "videos": videos}

@app.get("/api/export/csv")
async def export_csv():
    csv_data = manager.export_accounts_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=xnexus_accounts.csv"}
    )

@app.get("/api/export/json")
async def export_json():
    summary = manager.get_summary()
    return JSONResponse(
        content=summary,
        headers={"Content-Disposition": "attachment; filename=xnexus_metrics.json"}
    )

@app.get("/api/events")
async def events_stream(request: Request):
    q = await manager.subscribe_events()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            manager.unsubscribe_events(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
