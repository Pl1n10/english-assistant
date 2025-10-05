from fastapi import FastAPI
app = FastAPI(title="English Assistant Backend (minimal)")
@app.get("/")     def root():    return {"app": "english-assistant-backend"}
@app.get("/healthz")             def healthz(): return {"status": "ok"}
