"""
Import vnsl_articles.json vào Firestore collection "articles".

Usage:
    python import_articles.py

Requirements:
    pip install firebase-admin
"""

import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# ── Config ────────────────────────────────────────────────────────────────────

FIREBASE_JSON = "firebase.json"
ARTICLES_FILE = "data/articles/vnsl_articles.json"
COLLECTION    = "articles"

# ── Init Firebase ─────────────────────────────────────────────────────────────

cred = credentials.Certificate(FIREBASE_JSON)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ── Import ────────────────────────────────────────────────────────────────────

with open(ARTICLES_FILE, encoding="utf-8") as f:
    articles = json.load(f)

print(f"📄 Found {len(articles)} articles to import...")
print(f"📦 Target collection: {COLLECTION}\n")

success = 0
failed  = 0

for i, article in enumerate(articles):
    try:
        slug = article.get("slug") or article.get("article_id")
        if not slug:
            print(f"  ⚠️  Skipping article {i} — no slug or article_id")
            failed += 1
            continue

        db.collection(COLLECTION).document(slug).set(article)
        print(f"  ✅ [{i+1}/{len(articles)}] {article.get('era')} / {article.get('chapter_title')}")
        success += 1

    except Exception as e:
        print(f"  ❌ Failed [{i+1}] {article.get('slug')}: {e}")
        failed += 1

print(f"\n{'='*50}")
print(f"✅ Success: {success}")
print(f"❌ Failed:  {failed}")
print(f"📦 Collection: {COLLECTION}")
print(f"🔗 View at: https://console.firebase.google.com")