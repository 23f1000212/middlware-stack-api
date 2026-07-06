from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
from collections import defaultdict

app = FastAPI()

# ==========================================
# 🛑 EXACT VALUES BASED ON YOUR INPUT
MY_EMAIL = "23f1000212@ds.study.iitm.ac.in" 
EXAM_PAGE_ORIGIN = "https://exam.sanand.workers.dev"
# ==========================================

ALLOWED_ORIGINS = [
    "https://app-ah3n9p.example.com",
    EXAM_PAGE_ORIGIN
]

# --- Middleware 2: CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"] # Allows the grader to read the header
)

rate_limit_db = defaultdict(list)
RATE_LIMIT_MAX = 12
RATE_LIMIT_WINDOW_SEC = 10

# --- Middleware 1 & 3: Context & Rate Limiting ---
@app.middleware("http")
async def custom_stack_middleware(request: Request, call_next):
    # 1. Rate Limiting (Ignore CORS Preflights)
    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            current_time = time.time()
            active_timestamps = [
                ts for ts in rate_limit_db[client_id] 
                if current_time - ts < RATE_LIMIT_WINDOW_SEC
            ]
            if len(active_timestamps) >= RATE_LIMIT_MAX:
                rate_limit_db[client_id] = active_timestamps
                return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
            active_timestamps.append(current_time)
            rate_limit_db[client_id] = active_timestamps

    # 2. Request Context Propagation
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    request.state.request_id = request_id

    # Execute endpoint
    response = await call_next(request)

    # 3. Echo the ID in the response headers
    response.headers["X-Request-ID"] = request_id
    return response

# --- Endpoint ---
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": MY_EMAIL,
        "request_id": request.state.request_id
    }
