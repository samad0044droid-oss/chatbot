"""
Professional Website Chatbot - Backend
----------------------------------------
Client onboarding: ek URL do, poori website crawl ho jayegi aur
uska knowledge base ban jayega. Phir client ko ek chhota <script>
tag milega jo woh apni website pe laga sakta hai.

Run:
    pip install -r requirements.txt
    cp .env.example .env   # phir .env mein apni OPENAI_API_KEY daalein
    uvicorn main:app --reload --port 8000
"""

import os
import threading
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI

from crawler import crawl_website, chunk_pages, build_count_chunks
from store import save_client_kb, get_relevant_chunks, load_client_kb, client_exists

load_dotenv()

app = FastAPI(title="Website Chatbot API")

# In-memory job tracker for background onboarding (crawling large sites
# can take minutes, longer than most hosting platforms allow a single
# HTTP request to stay open, so we run it in a background thread).
JOBS = {}

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allowed_origins == "*" else allowed_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class OnboardRequest(BaseModel):
    url: str
    business_name: str
    max_pages: int = 30


class ChatRequest(BaseModel):
    client_id: str
    message: str
    history: list[dict] = []  # [{"role": "user"/"assistant", "content": "..."}]


def _run_onboarding_job(job_id, url, business_name, max_pages):
    """Actual crawling work, run in a background thread so the HTTP
    request that triggered it can return immediately (avoids platform
    timeouts on large crawls)."""
    try:
        pages, product_links_by_page, category_result_counts, theme_color = crawl_website(
            url, max_pages=max_pages
        )
        if not pages:
            JOBS[job_id] = {"status": "error", "detail": "Website se koi content nahi mila."}
            return

        chunks = chunk_pages(pages)
        chunks.extend(build_count_chunks(product_links_by_page, category_result_counts))

        client_id = uuid.uuid4().hex[:12]
        num_chunks = save_client_kb(client_id, business_name, url, chunks, theme_color)

        JOBS[job_id] = {
            "status": "done",
            "client_id": client_id,
            "business_name": business_name,
            "pages_crawled": len(pages),
            "chunks_saved": num_chunks,
            "theme_color_detected": theme_color,
            "embed_snippet": (
                f'<script src="https://YOUR-SERVER-DOMAIN/widget.js" '
                f'data-client-id="{client_id}" data-color="{theme_color}"></script>'
            ),
        }
    except Exception as e:
        JOBS[job_id] = {"status": "error", "detail": str(e)}


@app.post("/admin/onboard")
def onboard_client(req: OnboardRequest):
    """Naye client ki website crawl karna SHURU karta hai (background mein)
    aur turant ek job_id wapis deta hai. Progress check karne ke liye
    /admin/onboard/status/{job_id} use karein."""
    url = req.url if req.url.startswith("http") else f"https://{req.url}"

    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {"status": "running"}

    thread = threading.Thread(
        target=_run_onboarding_job,
        args=(job_id, url, req.business_name, req.max_pages),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "running"}


@app.get("/admin/onboard/status/{job_id}")
def onboard_status(job_id: str):
    """Onboarding job ka current status/result check karein."""
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job ID nahi mila.")
    return job


@app.post("/chat")
def chat(req: ChatRequest):
    """Widget yahan message bhejta hai, hum relevant content + GPT jawab dete hain."""
    if not client_exists(req.client_id):
        raise HTTPException(status_code=404, detail="Client ID nahi mila.")

    kb = load_client_kb(req.client_id)
    relevant = get_relevant_chunks(req.client_id, req.message)

    context_text = "\n\n".join(
        f"[{c['url']}]\n{c['text']}" for c in relevant
    ) or "Koi relevant content nahi mila."

    system_prompt = (
        f"Aap {kb['business_name']} ke liye ek professional customer-support "
        "chatbot hain. Neeche di gayi website content ke basis par sawalat ka "
        "jawab dein — dosti aur professional tareeqe se.\n\n"
        "SAKHT QAIDA — GINTI KE SAWAL: agar content mein '[GINTI INFO]' se "
        "shuru hone wali lines hon, to sirf unhi mein diye gaye asli number "
        "use karein — khud andaza mat lagayein. Har '[GINTI INFO — category "
        "'naam']' line ek ALAG category ka number hai.\n\n"
        "SAKHT QAIDA — AMBIGUOUS SAWAL: agar user ne generic sawal poocha ho "
        "(jaise 'themes kitni hain', bina yeh bataye WordPress ya Shopify ya "
        "koi aur platform), aur content mein ISI keyword se milti julti "
        "MULTIPLE categories mojood hon (jaise 'themes', 'shopify themes', "
        "'wordpress themes' alag alag numbers ke saath), to KISI EK ko khud "
        "se sahi maan kar mat bata dein. Iske bajaye SAARI matching "
        "categories ka breakdown dein, jaise: 'Themes mein yeh categories "
        "hain: Themes (359), Shopify (154). Kis category ke baare mein "
        "jaanna chahte hain?' — user ko khud specify karne dein.\n\n"
        "SAKHT QAIDA — NUMBERS: kabhi bhi koi specific number (price, Rs, $, "
        "quantity, duration, discount %) invent ya guess na karein. Agar "
        "exact number content mein LITERALLY maujood nahi hai, to woh number "
        "mat dein — sirf yeh kahein ke exact price/detail website pe check "
        "karein ya business se rabta karein.\n\n"
        "Agar jawab content mein bilkul na mile to saaf keh dein ke yeh "
        "maloomat available nahi, aur user ko business se seedha rabta karne "
        "ka mashwara dein.\n\n"
        f"WEBSITE CONTENT:\n{context_text}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(req.history[-10:])  # last 10 messages tak history rakho
    messages.append({"role": "user", "content": req.message})

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=700,
    )

    return {"reply": completion.choices[0].message.content}


@app.get("/widget.js")
def serve_widget():
    """Client ki website pe embed hone wali JS file serve karta hai."""
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "widget", "chatbot-widget.js"),
        media_type="application/javascript",
    )


@app.get("/")
def health():
    return {"status": "ok"}
