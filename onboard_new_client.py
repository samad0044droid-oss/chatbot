"""
Naya Client Onboard Karne Wali Script
----------------------------------------
Jab bhi koi naya client aaye, bas neeche di gayi lines
(CLIENT_URL, BUSINESS_NAME, MAX_PAGES) change karein aur yeh file run kar dein:

    python onboard_new_client.py

Zaroori: backend server (uvicorn main:app --reload --port 8000)
alag terminal mein pehle se chal raha hona chahiye.
"""

import requests

# ============================================================
# 👇 YAHAN SIRF YEH CHEEZEN BADALEIN JAB NAYA CLIENT AAYE 👇
# ============================================================

CLIENT_URL = "https://healixphysio.org"        # client ki website ka URL
BUSINESS_NAME = "HEALIX PHYSIO"                   # client ke business ka naam
MAX_PAGES = 150                              # zyada pages taake saari categories cover ho jayen

# ============================================================
# 👆 Neeche kuch bhi change karne ki zarurat nahi 👆
# ============================================================

SERVER_URL = "http://localhost:8000"  # jab live server pe deploy karein to yahan naya URL daalein


def onboard():
    print(f"\nOnboarding shuru: {BUSINESS_NAME} ({CLIENT_URL})")
    print("Website crawl ho rahi hai, thora time lagega...\n")

    response = requests.post(
        f"{SERVER_URL}/admin/onboard",
        json={"url": CLIENT_URL, "business_name": BUSINESS_NAME, "max_pages": MAX_PAGES},
        timeout=1800,
    )

    if response.status_code != 200:
        print("❌ Error:", response.json().get("detail", response.text))
        return

    data = response.json()
    print(data)
    print("✅ Client tayyar ho gaya!\n")
    print(f"Client ID       : {data['client_id']}")
    print(f"Pages Crawled    : {data['pages_crawled']}")
    print(f"Chunks Saved     : {data['chunks_saved']}")
    print("\nYeh embed code client ko de dein (apni server domain daal kar):\n")
    print(data["embed_snippet"])
    print()


if __name__ == "__main__":
    onboard()