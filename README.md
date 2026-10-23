# Peer Library

A student-to-student academic resource–sharing platform. Students can discover, search, filter, and download notes, past papers, syllabi, and other study materials. Registered students can contribute their own study resources with rich academic metadata and file attachments.

Peer Library supports both a **unified local monolith** (for zero-dependency development) and a **production-ready decoupled architecture**:
- **Frontend:** Pure static HTML5, CSS3, vanilla ES6 JavaScript, Bootstrap 5.3, and Font Awesome 6 deployed to **Vercel** with same-origin API proxy rewrites.
- **Backend:** Authoritative Python / Flask 3 API server running on **Render** under Gunicorn.
- **Production Database:** Managed PostgreSQL on **Supabase** (with connection pooling).
- **Production Storage:** Private **Supabase Storage** bucket with time-limited signed download URLs.

---

## Key features & user journeys

1. **Catalogue-first discovery** — Published resources appear immediately upon opening the platform; no query is required to browse materials.
2. **Multi-attribute search & filtering** — Partial, case-insensitive keyword search across title, description, subject, category, author, and roll number, combined with resource type filters (notes, paper, book, syllabus, link, other) and sorting (newest, oldest, most downloaded, title A–Z).
3. **Responsive pagination** — Clean pagination controls navigating results server-side or via JSON API.
4. **Detailed resource inspection** — Dedicated detail views with formatted, linkified descriptions (safe `http(s)` anchor tags only), academic metadata, and uploader attribution.
5. **Student accounts & session management** — Registration, login, and logout backed by secure scrypt password hashing (Werkzeug), Flask-Login session cookies, CSRF protection, and rate limiting.
6. **Secure multipart uploads** — Strict server-side extension allowlist (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`, `.docx`), 25 MiB size enforcement, magic-byte MIME signature verification (including DOCX ZIP container validation), and randomized UUID-based storage keys.
7. **Authorized, time-limited downloads** — Direct downloads checked against resource publication status and ownership. In production, downloads redirect to short-lived signed URLs from a private Supabase bucket.
8. **Defensive security & anti-XSS** — All user content is escaped (Jinja2) or constructed with safe DOM APIs (`textContent`, `setAttribute`), neutralizing stored-XSS payloads. Security headers (CSP, nosniff, frame-ancestors deny, strict referrer policy) are attached to every response.
9. **Dark & light theme** — Instant theme switching backed by `localStorage` without layout or color flicker on initial page load.
10. **Graceful feedback states** — Informative empty states, loading indicators, field-level validation feedback, and toast alerts for all mutating actions.

---

## Technology stack

| Component | Local Development | Production Target |
| :--- | :--- | :--- |
| **Frontend** | Jinja2 templates or static HTML/JS | Vanilla HTML/CSS/JS on **Vercel** |
| **Backend API** | Flask 3.0.3 development server | Gunicorn 23 on **Render** (Python 3.12) |
| **Database** | SQLite (`instance/peer_library.db`) | Managed PostgreSQL on **Supabase** |
| **Object Storage** | Local filesystem (`uploads/`) | Private bucket on **Supabase Storage** |
| **Migrations** | Flask-Migrate 4.0 (Alembic) | `flask db upgrade` (Render Build Command / Pre-Deploy) |
| **Auth & Security** | Flask-Login, Flask-WTF, Flask-Limiter | Session cookies (Lax/Secure) + CSRF + Rate Limiting |
| **Styling & Icons** | CSS3 custom properties, Bootstrap 5.3 CDN, Font Awesome 6 CDN, Inter Google Font |

---

## Project structure

```
peer_library/
├── frontend/                  # Static frontend ready for Vercel deployment
│   ├── css/styles.css         # Theme tokens, glassmorphism, responsive grid
│   ├── js/theme.js            # Instant theme initialization & toggle logic
│   ├── js/api.js              # Centralized API client (CSRF, cookies, auth check)
│   ├── js/app.js              # Catalogue live search, filters, pagination
│   ├── js/resource.js         # Single resource detail loader & download handler
│   ├── js/contribute.js       # Client-validated upload form with file preview
│   ├── js/auth.js             # Login & registration forms
│   ├── index.html             # Explore / Catalogue page
│   ├── resource.html          # Resource detail view
│   ├── contribute.html        # Resource submission form
│   ├── login.html             # Login view
│   ├── register.html          # Registration view
│   └── vercel.json            # Vercel configuration (for Root Directory = frontend)
├── migrations/                # Alembic migration versions and environment
├── static/                    # Flask server-rendered static assets
├── templates/                 # Server-rendered Jinja2 templates (dev monolith)
├── tests/                     # 87 automated pytest regression & unit tests
├── uploads/                   # Local file storage (development only)
├── .dockerignore              # Excludes .venv, git, and local databases from containers
├── .env.example               # Template environment configuration (placeholders only)
├── .gitignore                 # Excludes .venv, instance/*.db, uploads/*, and secrets
├── app.py                     # Application factory, CLI commands & Gunicorn entrypoint
├── auth.py                    # Auth blueprint (HTML forms & JSON API endpoints)
├── config.py                  # Environment-driven config & production startup validation
├── deploy.sh                  # Docker Compose deployment convenience script
├── docker-compose.yml         # Containerized local environment with named volumes
├── Dockerfile                 # Production container image (Python 3.12-slim, non-root)
├── entrypoint.sh              # Container startup script (runs migrations before server)
├── extensions.py              # Shared SQLAlchemy, Migrate, Login, CSRF, Limiter singletons
├── forms.py                   # WTForms validators for server-rendered routes
├── init_db.py                 # Dev-only helper to inspect table creation
├── migrate_legacy.py          # Idempotent importer for legacy sample SQLite data
├── models.py                  # User, Resource, ResourceFile data models
├── render.yaml                # Render Blueprint specification for native web service
├── requirements.txt           # Pinned production and development dependencies
├── security.py                # Safe redirect guards, URL linkify, security headers & CORS
├── services.py                # Resource search queries and upload lifecycle
├── storage.py                 # LocalStorage and SupabaseStorage adapters
├── SUPABASE_SETUP.md          # Step-by-step remote database and storage setup guide
├── validation.py              # Magic-byte MIME type and file-size verification
├── vercel.json                # Root Vercel proxy configuration (API rewrite proxy)
└── views.py                   # Main blueprint (catalogue, detail, uploads, downloads)
```

---

## Local installation & setup

### Prerequisites
- Python 3.11+ (3.12 recommended; Docker image uses 3.12-slim).
- `git`, `pip`, and `venv`.
- (Optional) Docker Desktop if running via containers.

### Windows PowerShell

```powershell
# 1. Clone repository and navigate to root
cd c:\MyPrograms\peer_library\peer_library

# 2. Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Set up environment configuration
Copy-Item .env.example .env
# Edit .env and set your SECRET_KEY (e.g., python -c "import secrets; print(secrets.token_hex(32))")

# 5. Apply database migrations to create local SQLite schema
$env:FLASK_APP = "app"
flask db upgrade

# 6. (Optional) Import legacy sample records
python migrate_legacy.py --dry-run     # Preview counts
python migrate_legacy.py               # Import records

# 7. Start the local Flask server
python app.py
# -> Backend and server-rendered frontend running at http://localhost:5000
```

### macOS / Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export FLASK_APP=app
flask db upgrade
python migrate_legacy.py
python app.py
```

### Running the static frontend locally

To test the decoupled Vercel static frontend locally against your running Flask backend:

```powershell
# In a separate terminal, serve the frontend directory:
python -m http.server -d frontend 3000
# Open http://localhost:3000 in your browser
```
*(Ensure `CORS_ALLOWED_ORIGINS=http://localhost:3000` is set in your `.env` when connecting directly cross-origin).*

---

## Running automated tests

The test suite runs 87 automated tests using an in-memory SQLite database and isolated temporary storage:

```powershell
$env:FLASK_ENV = "testing"
.\.venv\Scripts\python.exe -m pytest
```

---

## Running with Docker locally

```bash
docker compose up -d --build
# Open http://localhost:5000
docker compose logs -f web
docker compose down
```

The container runs as non-root user `appuser`, applies migrations once on startup via `entrypoint.sh`, binds to port `5000`, and preserves local data in named Docker volumes (`pl_instance`, `pl_uploads`).

---

## Production deployment architecture

```
                     +---------------------------------------+
                     |            User Browser               |
                     +-------------------+-------------------+
                                         |
                       https://peer-library.vercel.app
                                         |
                                         v
                     +---------------------------------------+
                     |            Vercel Frontend            |
                     |   (Static HTML/CSS/JS + Proxy Cache)  |
                     +-------------------+-------------------+
                                         |
                  /api/* and /download/* rewrites (Same-Origin)
                                         |
                                         v
                     +---------------------------------------+
                     |          Render Web Service           |
                     |   (Flask 3 + Gunicorn 23 Workers)     |
                     +---------+-------------------+---------+
                               |                   |
            PostgreSQL (Port 5432)        Signed URLs (HTTPS)
                               |                   |
                               v                   v
                     +-------------------+   +--------------------+
                     |  Supabase Postgres|   |  Supabase Storage  |
                     |  (Relational Data)|   |  (Private Bucket)  |
                     +-------------------+   +--------------------+
```

---

## 1. Backend deployment on Render

### Method A: Using Render Blueprint (`render.yaml`) — Recommended
1. Push your repository to your GitHub account (when ready).
2. Log into [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Connect your GitHub repository. Render reads `render.yaml` automatically.
5. In the environment configuration screen, fill in your secret variables:
   - `DATABASE_URL`: Your Supabase connection string:
     - **Render / IPv4:** Use Supabase's **Session Pooler** on port **`5432`** (`postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`).
     - **Direct Connection:** Or Direct Connection on port **`5432`** (`postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres`) if direct IPv6 routing is supported.
     - *Warning:* Do **not** use the Transaction Pooler (port `6543`) as it breaks prepared statements and session state in persistent Gunicorn workers. Obtain exact values from Supabase Dashboard **Connect**.
   - `SUPABASE_URL`: Your Supabase project URL (e.g., `https://<project-ref>.supabase.co`).
   - `SUPABASE_SERVICE_KEY`: Your Supabase `service_role` secret key.
   - `SUPABASE_BUCKET`: `resources`.
6. Click **Apply**.
   - **Free Plan Migration Strategy:** Render's Free plan does not support `preDeployCommand`. Migrations run safely during the build phase via `buildCommand: pip install -r requirements.txt && python -m flask --app app db upgrade`. This executes once per build on the build runner, utilizes the configured environment variables, avoids concurrent worker races, and halts deployment on error. (If upgrading to a paid **Starter** plan, you can switch to `preDeployCommand: python -m flask --app app db upgrade`).
   - Render then starts Gunicorn on `0.0.0.0:$PORT` and monitors `/healthz`.

### Method B: Manual Web Service on Render
- **Environment:** Python 3
- **Plan:** Free (or Starter)
- **Build Command:** `pip install -r requirements.txt && python -m flask --app app db upgrade`
- **Pre-Deploy Command:** Leave blank on Free plan. (Only if using Starter plan: `python -m flask --app app db upgrade`).
- **Start Command:** `gunicorn -w 4 -b 0.0.0.0:$PORT --access-logfile - app:app`
- **Health Check Path:** `/healthz`
- **Environment Variables:** Set according to the Environment Variables table below.

---

## 2. Frontend deployment on Vercel

Peer Library's static frontend requires **zero build commands** and no Node.js compilation.

> **Deployment Sequence Note:**  
> Deploy your backend on Render **first** before deploying the frontend on Vercel. Render assigns your backend service a live URL upon provisioning (e.g. `https://peer-library-api.onrender.com` or `https://peer-library-api-xxxx.onrender.com`). You will need this actual URL to configure the Vercel proxy.

1. Log into [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project** and import your Git repository.
3. Configure the project:
   - **Framework Preset:** Other / None.
   - **Root Directory:** Either leave as repository root `./` (uses root `vercel.json`), or select `frontend` (uses `frontend/vercel.json`).
   - **Build Command:** Leave blank (no build step).
   - **Output Directory:** Leave blank.
4. **Update the Proxy Destination:**  
   Open `vercel.json` (and `frontend/vercel.json`), locate the proxy rewrites, and replace `https://YOUR-RENDER-BACKEND.onrender.com` with your real Render web service URL:
   ```json
   {
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://<your-service-name>.onrender.com/api/:path*"
       },
       {
         "source": "/download/:path*",
         "destination": "https://<your-service-name>.onrender.com/download/:path*"
       }
     ]
   }
   ```
5. Click **Deploy**. Vercel publishes the static site on your global `.vercel.app` domain.

> **Why the Vercel Proxy Rewrite is Superior:**  
> The Vercel rewrite forwards `/api/*` and `/download/*` requests to Render at the edge. To the browser, all API calls and downloads are **same-origin**, which means:
> - Flask session cookies work as standard first-party cookies with `SameSite=Lax`.
> - CSRF tokens are validated seamlessly without browser cookie blocking.
> - No cross-origin preflight latency on standard requests.

---

## 3. Supabase production database & storage

See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for full screenshots and detailed instructions.

In brief:
1. Create a project at [supabase.com](https://supabase.com).
2. Under **Connect** (or *Project Settings → Database*), select **Connection Pooling** with mode **Session** (port `5432`), or **Direct Connection** (port `5432` if IPv6 supported). Copy the connection URI into `DATABASE_URL`. Do **not** use the Transaction Pooler (port `6543`).
3. Under *Project Settings → API*, copy `Project URL` to `SUPABASE_URL` and `service_role` secret to `SUPABASE_SERVICE_KEY`.
4. Under *Storage → Buckets*, create a new bucket named `resources`. **Keep "Public bucket" disabled (OFF)**.
5. Run migrations against Supabase (handled automatically during Render `buildCommand`, or manually via `python -m flask --app app db upgrade`).

---

## Environment variables reference

| Variable | Platform | Example / Description | Secret? |
| :--- | :--- | :--- | :---: |
| `FLASK_ENV` | Render | `production` | No |
| `SECRET_KEY` | Render | Cryptographic random hex (`python -c "import secrets; print(secrets.token_hex(32))"`) | **YES** |
| `DATABASE_URL` | Render | `postgresql://postgres.<project-ref>:<pass>@aws-0-<region>.pooler.supabase.com:5432/postgres` | **YES** |
| `STORAGE_BACKEND` | Render | `supabase` (refuses to start with local storage in production) | No |
| `SUPABASE_URL` | Render | `https://<project-ref>.supabase.co` | No |
| `SUPABASE_SERVICE_KEY` | Render | `service_role` secret token (bypasses storage RLS server-side) | **YES** |
| `SUPABASE_BUCKET` | Render | `resources` (must match private bucket name) | No |
| `SUPABASE_SIGNED_URL_TTL` | Render | `120` (signed download URL expiry in seconds) | No |
| `SESSION_COOKIE_SECURE` | Render | `true` (enforces HTTPS-only cookies in production) | No |
| `SESSION_COOKIE_SAMESITE` | Render | `Lax` (recommended with Vercel rewrite proxy) | No |
| `CORS_ALLOWED_ORIGINS` | Render | `https://peer-library.vercel.app` (optional if using proxy) | No |

---

## End-to-end production smoke test

Execute this verification procedure after deploying to Render, Vercel, and Supabase:

1. **Verify Backend Health:**
   ```bash
   curl -i https://YOUR-RENDER-BACKEND.onrender.com/healthz
   # Expect: HTTP/1.1 200 OK {"status":"ok"}
   ```
2. **Open Vercel Frontend:**
   Navigate to `https://YOUR-APP.vercel.app`. The catalogue should render without errors, showing existing published resources or the empty catalogue state.
3. **Register a Test Account:**
   Click **Sign up**, enter name, email, and password. Verify immediate login and redirect to the catalogue with user menu displayed in the navbar.
4. **Publish a Resource with Attachment:**
   Click **Contribute**, fill in title, subject, category, description, and attach a valid `.pdf` or `.png` file (`<= 25 MiB`). Click **Add to Library**.
5. **Verify Database Persistence:**
   In your Supabase Dashboard **Table Editor**, confirm a new row appears in `resources` with matching `uploader_id`, and a row in `resource_files` with a generated UUID storage key.
6. **Verify Storage Bucket:**
   In Supabase Dashboard **Storage → resources**, confirm the file is stored under its UUID key.
7. **Verify Download:**
   On the resource detail page, click **Download**. Verify the server issues a 302 redirect to a signed Supabase URL and the file downloads cleanly.
8. **Verify Search:**
   Type a keyword from the title or subject into the search bar. Verify results filter dynamically within 300ms.
9. **Verify Logout:**
   Click **Log out**. Verify user session terminates and the contribute page redirects unauthenticated visitors to login.

---

## Operations & security guidelines

- **Local vs. Production Storage:** Local storage (`uploads/`) is purely for development. Render web containers have ephemeral filesystems; all uploads will be lost on container restart unless `STORAGE_BACKEND=supabase` is configured.
- **Fail-Fast Configuration Guard:** The backend application refuses to start in production if `SECRET_KEY` is default, `DATABASE_URL` is SQLite, or Supabase credentials are missing.
- **Migration Management:** Never run `db.create_all()` in production. Always manage schema updates via `flask db migrate -m "..."` and apply them with `flask db upgrade`.
- **Credential Protection:** `SUPABASE_SERVICE_KEY`, database passwords, and `SECRET_KEY` must **never** be included in frontend code, public repositories, or client-side JavaScript.
- **Academic Identity Verification:** Student roll numbers and departments entered during registration are self-reported and explicitly displayed as **unverified**; registering an account does not verify institutional enrollment.
