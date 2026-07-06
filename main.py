import time
import uuid
import os 
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ==========================================
# CONSTANTS
# ==========================================
EMAIL = "23f1000212@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = os.getenv(
    "Q10_ALLOWED_ORIGIN",
    "https://app-ah3n9p.example.com"
)

RATE_LIMIT = int(
    os.getenv("Q10_RATE_LIMIT", "12")
)

WINDOW = 10

# ==========================================
# MIDDLEWARE 2: CORS POLICY
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        "https://exam.sanand.workers.dev",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)
# ==========================================
# MIDDLEWARE 1 & 3: CONTEXT & RATE LIMITER
# ==========================================
client_hits = defaultdict(list)
RATE_LIMIT = 12
WINDOW = 10

@app.middleware("http")
async def custom_stack_middleware(request: Request, call_next):
    # --- STEP 1: Request Context ---
    # Always extract or generate the X-Request-ID first
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = str(uuid.uuid4())
    
    # Store it in the request state for the endpoint to use
    request.state.request_id = req_id

    # --- STEP 2: Rate Limiting ---
    # We explicitly ignore OPTIONS requests so CORS preflights always pass
    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            
            # Clean up old timestamps outside the 10-second window
            hits = [t for t in client_hits[client_id] if now - t < WINDOW]
            
            # Check if they have hit the 12 request limit
            if len(hits) >= RATE_LIMIT:
                client_hits[client_id] = hits # Update state before rejecting
                
                # Return 429 early, but make sure to attach the Request ID!
                response = JSONResponse(
                    status_code=429, 
                    content={"detail": "Too Many Requests"}
                )
                response.headers["X-Request-ID"] = req_id
                return response
            
            # Otherwise, record this new request timestamp
            hits.append(now)
            client_hits[client_id] = hits

    # --- STEP 3: Execute the Endpoint ---
    response = await call_next(request)
    
    # --- STEP 4: Outbound Headers ---
    # Attach the Request ID to the successful response
    response.headers["X-Request-ID"] = req_id
    return response

# ==========================================
# ENDPOINT
# ==========================================
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
