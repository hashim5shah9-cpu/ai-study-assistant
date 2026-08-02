from fastapi import FastAPI

app = FastAPI()

@app.get("/")
@app.get("/health")
@app.get("/api/health")
def root():
    return {"status": "online", "message": "Vercel Python serverless backend is live!"}
