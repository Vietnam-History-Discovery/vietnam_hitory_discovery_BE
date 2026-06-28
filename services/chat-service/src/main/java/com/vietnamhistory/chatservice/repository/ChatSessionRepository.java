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
import java.util.concurrent.ExecutionException;

@Repository
public class ChatSessionRepository {

    private static final Logger log = LoggerFactory.getLogger(ChatSessionRepository.class);

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
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore findById interrupted for id={}", id, e);
        } catch (ExecutionException e) {
            log.error("Firestore findById failed for id={}", id, e);
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
                ChatSession session = doc.toObject(ChatSession.class);
                if (session != null) {
                    session.setId(doc.getId());
                }
                sessions.add(session);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore findByUserId interrupted for userId={}", userId, e);
        } catch (ExecutionException e) {
            log.error("Firestore findByUserId failed for userId={}", userId, e);
        }
        return sessions;
    }

    public ChatSession save(ChatSession session) {
        try {
            if (session.getId() == null) {
                session.setId(java.util.UUID.randomUUID().toString());
            }
            if (session.getCreatedAt() == null) {
                session.setCreatedAt(java.time.LocalDateTime.now().toString());
            }
            if (session.getUpdatedAt() == null) {
                session.setUpdatedAt(session.getCreatedAt());
            }
            getFirestore().collection("chat_sessions").document(session.getId()).set(session).get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore save interrupted for session={}", session.getId(), e);
        } catch (ExecutionException e) {
            log.error("Firestore save failed for session={}", session.getId(), e);
        }
        return session;
    }

    public void delete(ChatSession session) {
        try {
            getFirestore().collection("chat_sessions").document(session.getId()).delete().get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore delete interrupted for session={}", session.getId(), e);
        } catch (ExecutionException e) {
            log.error("Firestore delete failed for session={}", session.getId(), e);
        }
    }
}
