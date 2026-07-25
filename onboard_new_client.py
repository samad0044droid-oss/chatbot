"""
Naya Client Onboard Karne Wali Script (Background Job Version)
------------------------------------------------------------------
Jab bhi koi naya client aaye, bas neeche di gayi lines
(CLIENT_URL, BUSINESS_NAME, MAX_PAGES) change karein aur yeh file run kar dein:

    python onboard_new_client.py

Yeh ab background job ke zariye kaam karta hai — pehle crawling
"shuru" hoti hai, phir yeh script har 5 second mein status check karti
rehti hai jab tak crawling complete na ho jaye. Isse bade websites
(150+ pages) bhi bina timeout ke crawl ho sakti hain, chahe local ho
ya Railway jaisi hosting pe.
"""

import time
import requests

# ============================================================
# 👇 YAHAN SIRF YEH CHEEZEN BADALEIN JAB NAYA CLIENT AAYE 👇
# ============================================================

CLIENT_URL = "https://healixphysio.org"     # client ki website ka URL
BUSINESS_NAME = "HEALIX PHYSIO"              # client ke business ka naam
MAX_PAGES = 150                              # zyada pages taake saari categories cover ho jayen

# ============================================================
# 👆 Neeche kuch bhi change karne ki zarurat nahi 👆
# ============================================================

SERVER_URL = "https://chatbot-production-eade.up.railway.app"  # apka live Railway URL


def onboard():
    print(f"\nOnboarding shuru: {BUSINESS_NAME} ({CLIENT_URL})")

    # Step 1: job shuru karo
    start_resp = requests.post(
        f"{SERVER_URL}/admin/onboard",
        json={"url": CLIENT_URL, "business_name": BUSINESS_NAME, "max_pages": MAX_PAGES},
        timeout=30,
    )

    if start_resp.status_code != 200:
        print("❌ Error shuru karte waqt:", start_resp.text)
        return

    job_id = start_resp.json()["job_id"]
    print(f"Job shuru ho gaya (ID: {job_id})")
    print("Website crawl ho rahi hai, thora time lagega... (status check har 5 second)\n")

    # Step 2: poll karte raho jab tak complete na ho
    while True:
        time.sleep(5)
        status_resp = requests.get(f"{SERVER_URL}/admin/onboard/status/{job_id}", timeout=30)

        if status_resp.status_code != 200:
            print("❌ Status check karte waqt error:", status_resp.text)
            return

        data = status_resp.json()
        status = data.get("status")

        if status == "running":
            print("...abhi bhi crawl ho rahi hai, wait karein...")
            continue

        if status == "error":
            print("❌ Error:", data.get("detail"))
            return

        if status == "done":
            print("✅ Client tayyar ho gaya!\n")
            print(f"Client ID       : {data['client_id']}")
            print(f"Pages Crawled   : {data['pages_crawled']}")
            print(f"Chunks Saved    : {data['chunks_saved']}")
            print(f"Theme Color     : {data['theme_color_detected']}")
            print("\nYeh embed code client ko de dein (apni server domain daal kar):\n")
            print(data["embed_snippet"])
            print()
            return


if __name__ == "__main__":
    onboard()
