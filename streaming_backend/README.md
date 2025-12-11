# StreamView Backend (FastAPI)

## Overview

StreamView Backend is a FastAPI service that powers a small Netflix-style streaming application. It is responsible for:

- User authentication using JWT access tokens
- Managing video and category metadata stored in a SQLite database via SQLAlchemy
- Exposing REST APIs for videos, categories, and authentication
- Proxying and streaming remote MP4 content with HTTP Range support to the frontend

The typical development setup runs the backend on port **3001** and the React/Tailwind frontend on port **3000**.

## Prerequisites

- Python 3.10+ (recommended)
- `pip` for installing Python packages

All backend dependencies are declared in `requirements.txt`.

## Installation

From the backend container root (`streamview-platform-221741/streaming_backend`):

```bash
# 1. Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate           # Linux/macOS
# .venv\Scripts\activate            # Windows

# 2. Install dependencies
pip install -r requirements.txt
```

The SQLite database file will be created automatically under `data/app.db` on startup, and seeded with demo data.

## Running the Backend Locally

From `streamview-platform-221741/streaming_backend`:

```bash
# Default development run (will bind to 0.0.0.0:3001 for local use)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001
```

Once running, you can access:

- Health check: <http://localhost:3001/>
- OpenAPI/Swagger UI: <http://localhost:3001/docs>
- OpenAPI JSON: <http://localhost:3001/openapi.json>

In the KAVIA preview environment, the backend is typically reachable at a URL similar to:

- `https://<preview-host>:3001`

Use this base URL when configuring the frontend for remote previews.

## Environment Configuration (JWT settings)

JWT configuration for authentication is driven by environment variables read in `src/api/routers/auth.py`:

- `JWT_SECRET`  
  Secret key used to sign JWT access tokens.  
  **Required for any real environment**; the code falls back to a development default (`"dev-secret-change-me"`) if not set.

- `JWT_ALGORITHM`  
  Algorithm used by PyJWT for signing tokens.  
  Default: `HS256`.

- `JWT_EXPIRE_MINUTES`  
  Token lifetime in minutes.  
  Default: `60`.

Example `.env` for local development:

```bash
JWT_SECRET=super-secret-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

You can export these in your shell before starting Uvicorn:

```bash
export JWT_SECRET=super-secret-change-me
export JWT_ALGORITHM=HS256
export JWT_EXPIRE_MINUTES=60

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001
```

## CORS and Frontend Integration

The backend enables permissive CORS in `src/api/main.py`:

- `allow_origins=["*"]`
- `allow_methods=["*"]`
- `allow_headers=["*", "Authorization", "Range"]`
- `expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "Content-Type"]`

This allows the React frontend running on port 3000 or from a preview URL to call the backend without additional configuration and ensures that video streaming headers are visible to the browser.

In production, you should restrict `allow_origins` to the actual frontend origin.

## API Endpoints Overview

The backend exposes the following key endpoints (see `interfaces/openapi.json` and the router modules under `src/api/routers` for full details):

### Health

- `GET /`  
  Returns a simple JSON health response after touching the database connection.  
  **Response**: `{ "message": "Healthy" }`

### Authentication (`src/api/routers/auth.py`)

- `POST /auth/signup`  
  Create a new user account and return a JWT access token.

  - Request body (`application/json`):

    ```json
    {
      "email": "user@example.com",
      "password": "plain-text-password"
    }
    ```

  - Responses:
    - `200 OK`: `{ "access_token": "...", "token_type": "bearer" }`
    - `400 Bad Request`: Email already registered
    - `422 Unprocessable Entity`: Validation errors

- `POST /auth/login`  
  Authenticate by email and password and return a JWT access token.

  - Request body (`application/json`):

    ```json
    {
      "email": "user@example.com",
      "password": "plain-text-password"
    }
    ```

  - Responses:
    - `200 OK`: `{ "access_token": "...", "token_type": "bearer" }`
    - `401 Unauthorized`: Invalid credentials
    - `422 Unprocessable Entity`: Validation errors

- `GET /auth/me`  
  Return the currently authenticated user.

  - Requires `Authorization: Bearer <access_token>` header.
  - **Response example**:

    ```json
    {
      "id": 1,
      "email": "user@example.com",
      "full_name": "Demo User",
      "created_at": "2025-01-01T00:00:00Z"
    }
    ```

### Videos (`src/api/routers/videos.py`)

- `GET /videos/`  
  List videos with optional search and category filters.

  - Query parameters:
    - `q` (optional): Text search applied to video `title`.
    - `category_id` (optional): Numeric category ID filter.
    - `category` (optional): Alias for category filtering; if integer-like, treated as `category_id`.

  - Example:

    ```http
    GET /videos/?q=bunny&category_id=1
    ```

  - Response: List of `Video` objects, each including categories (see `src/db/schemas.py`).

- `GET /videos/{video_id}`  
  Get video metadata by ID.

  - Path parameter:
    - `video_id` (integer): Video ID.

  - Responses:
    - `200 OK`: A `Video` object.
    - `404 Not Found`: Video not found.

### Categories (`src/api/routers/categories.py`)

- `GET /categories/`  
  List all categories.

  - Response: Array of `Category` objects:

    ```json
    [
      { "id": 1, "name": "Action" },
      { "id": 2, "name": "Drama" },
      { "id": 3, "name": "Documentary" }
    ]
    ```

### Streaming (`src/api/routers/stream.py`)

- `GET /stream/{video_id}`  
  Proxy and stream video bytes from the `video_url` field of the specified video.

  - Path parameter:
    - `video_id` (integer): Video ID (must exist in the database).
  - Headers:
    - Optional `Range` header, e.g. `Range: bytes=0-`, for seeking.

  - Behavior:
    - Fetches the `video_url` from the `videos` table.
    - Uses `aiohttp` to request the remote MP4.
    - Forwards the `Range` header to the upstream server when present.
    - Mirrors key upstream headers in the response:
      - `Content-Type`
      - `Content-Length`
      - `Accept-Ranges`
      - `Content-Range`
    - Preserves the upstream status (`200 OK` or `206 Partial Content`).
    - On upstream errors, returns a FastAPI `HTTPException` with the upstream status code and message.

The React frontend expects this endpoint to be available at:

```text
GET {API_BASE_URL}/stream/{id}
```

where `API_BASE_URL` is typically `http://localhost:3001` during local development.

## Database and Seeding

The backend uses SQLite with SQLAlchemy:

- Database file: `data/app.db`
- Models: `src/db/models.py`
- Schemas: `src/db/schemas.py`
- Session and engine: `src/db/session.py`

On startup, the `on_startup` handler in `src/api/main.py`:

1. Ensures all tables exist (`Base.metadata.create_all`).
2. Calls `init_db_and_seed` from `src/db/seed.py` to:
   - Create a default demo user (`demo@streamview.local` / `demopassword`).
   - Seed categories (`Action`, `Drama`, `Documentary`).
   - Seed several sample videos pointing at public MP4 URLs from Google’s sample video bucket.

This means a fresh clone can be run immediately and will have data ready for browsing and streaming.

## Outbound Internet and Streaming Requirements

The streaming feature relies on fetching remote MP4 files from public URLs, such as:

- `https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4`

To function correctly, the backend process must have **outbound internet access** to these domains. If outbound access is blocked:

- `/stream/{id}` requests may fail with 4xx/5xx errors.
- The frontend video player will show an error state when the `<video>` element cannot load the stream.

## Typical Local End-to-End Setup

1. Start the backend:

   ```bash
   cd streamview-platform-221741/streaming_backend
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001
   ```

2. Start the frontend (in a separate terminal):

   ```bash
   cd streamview-platform-221742/streaming_frontend
   npm install
   npm start
   ```

3. Open the frontend:

   - <http://localhost:3000>

   The frontend will, by default, target `http://localhost:3001` for its API base URL if `REACT_APP_API_BASE_URL` is not set.

## Troubleshooting Streaming Issues

If video playback fails or stalls in the frontend:

1. **Check backend reachability**

   - From a browser, open <http://localhost:3001/> and confirm you see the JSON health response.
   - Open <http://localhost:3001/docs> and confirm the Swagger UI loads.
   - If using a preview environment, ensure you are using the provided backend URL (e.g. `https://<preview-host>:3001`).

2. **Verify frontend API base URL**

   - Ensure the frontend is configured to point at the correct backend base URL:
     - For local dev: `REACT_APP_API_BASE_URL=http://localhost:3001`
     - For previews: `REACT_APP_API_BASE_URL=https://<preview-host>:3001`
   - Confirm that `/videos`, `/categories`, and `/stream/{id}` calls succeed in the browser dev tools Network tab.

3. **Confirm JWT configuration and token presence**

   - Sign up or log in through the frontend or manually hit `POST /auth/signup` or `POST /auth/login`.
   - Verify a `token` entry exists in `localStorage` (the frontend stores the JWT under key `token`).
   - Check that requests from the frontend include `Authorization: Bearer <token>` when necessary.

4. **Check outbound internet access**

   - Look at backend logs around `/stream/{id}` requests for errors from `aiohttp`.
   - If the backend cannot resolve or reach `commondatastorage.googleapis.com` (or other sample video hosts), the stream will fail.
   - In restricted environments, consider replacing seeded `video_url` values with URLs reachable inside your network.

5. **CORS issues**

   - If the browser console reports CORS errors, confirm that:
     - You are hitting the backend on the expected origin and port.
     - The backend is running with the default permissive CORS settings.
   - For advanced scenarios or production deployments, tighten `allow_origins` in `src/api/main.py` to your frontend origin and test again.

## Regenerating OpenAPI Specification

An auxiliary script (`src/api/generate_openapi.py`) can regenerate `interfaces/openapi.json` from the running FastAPI application:

```bash
cd streamview-platform-221741/streaming_backend
python -m src.api.generate_openapi
```

This will update `interfaces/openapi.json` with the current API schema.

## Summary of Key Endpoints

- `GET /` – Health check
- `POST /auth/signup` – Create account, return JWT
- `POST /auth/login` – Authenticate, return JWT
- `GET /auth/me` – Get current authenticated user
- `GET /videos/` – List videos (supports `q`, `category_id`, `category`)
- `GET /videos/{video_id}` – Get video metadata by ID
- `GET /categories/` – List all categories
- `GET /stream/{video_id}` – Proxy/stream video bytes with Range support
