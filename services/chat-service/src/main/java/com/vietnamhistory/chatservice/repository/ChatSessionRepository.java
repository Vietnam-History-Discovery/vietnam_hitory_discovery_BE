package com.vietnamhistory.chatservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.Query;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.chatservice.entity.ChatSession;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ExecutionException;

@Repository
public class ChatSessionRepository {

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public Optional<ChatSession> findById(String id) {
        try {
            var doc = getFirestore().collection("chat_sessions").document(id).get().get();
            if (doc.exists()) {
                return Optional.ofNullable(doc.toObject(ChatSession.class));
            }
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
        return Optional.empty();
    }

    public List<ChatSession> findByUserIdOrderByUpdatedAtDesc(String userId) {
        List<ChatSession> sessions = new ArrayList<>();
        try {
            var query = getFirestore().collection("chat_sessions")
                    .whereEqualTo("userId", userId)
                    .orderBy("updatedAt", Query.Direction.DESCENDING)
                    .get().get();
            for (var doc : query.getDocuments()) {
                sessions.add(doc.toObject(ChatSession.class));
            }
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
        return sessions;
    }

    public ChatSession save(ChatSession session) {
        if (session.getId() == null) {
            session.setId(java.util.UUID.randomUUID().toString());
        }
        getFirestore().collection("chat_sessions").document(session.getId()).set(session);
        return session;
    }

    public void delete(ChatSession session) {
        getFirestore().collection("chat_sessions").document(session.getId()).delete();
    }
}
