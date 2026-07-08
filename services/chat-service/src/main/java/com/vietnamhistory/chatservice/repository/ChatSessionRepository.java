package com.vietnamhistory.chatservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.Query;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.chatservice.entity.ChatSession;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;

@Repository
public class ChatSessionRepository {

    private static final Logger log = LoggerFactory.getLogger(ChatSessionRepository.class);
    private static final java.util.Map<String, ChatSession> inMemorySessions = new ConcurrentHashMap<>();

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public Optional<ChatSession> findById(String id) {
        try {
            var doc = getFirestore().collection("chat_sessions").document(id).get().get();
            if (doc.exists()) {
                ChatSession session = doc.toObject(ChatSession.class);
                if (session != null) {
                    session.setId(doc.getId());
                }
                return Optional.ofNullable(session);
            }
        } catch (Exception e) {
            log.error("Firestore findById failed for id={}, falling back to in-memory", id, e);
        }
        return Optional.ofNullable(inMemorySessions.get(id));
    }

    public List<ChatSession> findByUserIdOrderByUpdatedAtDesc(String userId) {
        List<ChatSession> sessions = new ArrayList<>();
        try {
            var query = getFirestore().collection("chat_sessions")
                    .whereEqualTo("userId", userId)
                    .orderBy("updatedAt", Query.Direction.DESCENDING)
                    .get().get();
            for (var doc : query.getDocuments()) {
                ChatSession session = doc.toObject(ChatSession.class);
                if (session != null) {
                    session.setId(doc.getId());
                }
                sessions.add(session);
            }
            return sessions;
        } catch (Exception e) {
            log.error("Firestore findByUserId failed for userId={}, falling back to in-memory", userId, e);
        }

        inMemorySessions.values().stream()
                .filter(session -> userId.equals(session.getUserId()))
                .sorted((s1, s2) -> {
                    String u1 = s1.getUpdatedAt() != null ? s1.getUpdatedAt() : "";
                    String u2 = s2.getUpdatedAt() != null ? s2.getUpdatedAt() : "";
                    return u2.compareTo(u1);
                })
                .forEach(sessions::add);
        return sessions;
    }

    public ChatSession save(ChatSession session) {
        if (session.getId() == null) {
            session.setId(java.util.UUID.randomUUID().toString());
        }
        if (session.getCreatedAt() == null) {
            session.setCreatedAt(java.time.LocalDateTime.now().toString());
        }
        if (session.getUpdatedAt() == null) {
            session.setUpdatedAt(session.getCreatedAt());
        }
        try {
            getFirestore().collection("chat_sessions").document(session.getId()).set(session).get();
        } catch (Exception e) {
            log.error("Firestore save failed for session={}, saving to in-memory", session.getId(), e);
        }
        inMemorySessions.put(session.getId(), session);
        return session;
    }

    public void delete(ChatSession session) {
        inMemorySessions.remove(session.getId());
        try {
            getFirestore().collection("chat_sessions").document(session.getId()).delete().get();
        } catch (Exception e) {
            log.error("Firestore delete failed for session={}", session.getId(), e);
        }
    }
}
