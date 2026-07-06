from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

EMAIL = "23f1000212@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-ah3n9p.example.com",
    "https://exam.sanand.workers.dev"
]

RATE_LIMIT = 12
WINDOW = 10

rate_limit_store = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


@app.middleware("http")
async def middleware(request: Request, call_next):

    # -----------------------
    # Request ID
    # -----------------------

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # -----------------------
    # Rate Limiting
    # -----------------------

    if request.url.path == "/ping":

        client = request.headers.get("X-Client-Id", "default")

        now = time.time()

        history = rate_limit_store.get(client, [])

        history = [t for t in history if now - t < WINDOW]

        if len(history) >= RATE_LIMIT:
            return Response(
                status_code=429,
                headers={
                    "Retry-After": str(WINDOW),
                    "X-Request-ID": request_id
                }
            )

        history.append(now)

        rate_limit_store[client] = history

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }


@app.get("/")
async def home():

    return {
        "status": "running"
    }
