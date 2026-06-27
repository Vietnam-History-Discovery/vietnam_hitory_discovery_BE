import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebase.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
docs = db.collection('chat_messages').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(10).stream()
for doc in docs:
    print(doc.to_dict())
