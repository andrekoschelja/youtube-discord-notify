# -*- coding: utf-8 -*-
"""
YouTube -> Discord Benachrichtigung (Cloud-Version fuer GitHub Actions)
Postet einen Link in deinen Discord-Channel, wenn ein NEUES Video kommt.
Shorts werden automatisch UEBERSPRUNGEN.

Unterschied zur Mac-Version:
- Laeuft NICHT in einer Endlosschleife, sondern macht EINE Pruefung pro Aufruf.
  (GitHub startet das Skript automatisch alle paar Minuten.)
- Die Webhook-Adresse kommt aus einem geheimen "Secret", nicht aus dem Code.
"""

import os
import json
import xml.etree.ElementTree as ET
import requests


# ============================================================
# EINSTELLUNGEN
# ============================================================

# Deine YouTube-Kanal-ID (nicht geheim, darf im Code stehen).
CHANNEL_ID = "UChsVtFRkiwb61uTqZJhBwng"

# Die Webhook-Adresse kommt aus dem GitHub-Secret (geheim, NICHT im Code).
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# ============================================================

SEEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesehene_videos.json")

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def lade_gesehene():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def speichere_gesehene(gesehene):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(gesehene), f)


def hole_videos():
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID
    antwort = requests.get(url, timeout=20)
    antwort.raise_for_status()
    wurzel = ET.fromstring(antwort.content)
    videos = []
    for eintrag in wurzel.findall("atom:entry", NS):
        video_id = eintrag.find("yt:videoId", NS).text
        titel = eintrag.find("atom:title", NS).text
        videos.append((video_id, titel))
    return videos


def ist_short(video_id):
    """200 = Short, 3xx (Umleitung) = normales Video. Consent-Cookie noetig."""
    url = "https://www.youtube.com/shorts/" + video_id
    try:
        antwort = requests.head(
            url,
            allow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0"},
            cookies={"SOCS": "CAI", "CONSENT": "YES+cb"},
            timeout=20,
        )
        return antwort.status_code == 200
    except requests.RequestException:
        return False


def poste_zu_discord(video_id):
    link = "https://www.youtube.com/watch?v=" + video_id
    nachricht = (
        "Andre hat JETZT ein neues YouTube Video gepostet... "
        "gerne vorbeischauen!! @everyone\n" + link
    )
    daten = {
        "content": nachricht,
        "allowed_mentions": {"parse": ["everyone"]},
    }
    antwort = requests.post(DISCORD_WEBHOOK_URL, json=daten, timeout=20)
    antwort.raise_for_status()


def main():
    if not DISCORD_WEBHOOK_URL:
        print("FEHLER: Kein DISCORD_WEBHOOK_URL gesetzt (GitHub-Secret fehlt).")
        return

    erster_lauf = not os.path.exists(SEEN_FILE)
    gesehene = lade_gesehene()
    videos = hole_videos()

    for video_id, titel in videos:
        if video_id in gesehene:
            continue

        if erster_lauf:
            gesehene.add(video_id)
            continue

        if ist_short(video_id):
            print("Uebersprungen (Short):", titel)
            gesehene.add(video_id)
            continue

        print("Poste neues Video:", titel)
        poste_zu_discord(video_id)
        gesehene.add(video_id)

    speichere_gesehene(gesehene)
    print("Pruefung fertig.")


if __name__ == "__main__":
    main()
