package com.vietnamhistory.chatservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.chatservice.entity.ChatMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ExecutionException;

@Repository
public class ChatMessageRepository {

    private static final Logger log = LoggerFactory.getLogger(ChatMessageRepository.class);

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public List<ChatMessage> findBySessionIdOrderByCreatedAtAsc(String sessionId) {
        List<ChatMessage> messages = new ArrayList<>();
        try {
            var query = getFirestore().collection("chat_messages")
                    .whereEqualTo("sessionId", sessionId)
                    .get().get();
            for (var doc : query.getDocuments()) {
                ChatMessage msg = doc.toObject(ChatMessage.class);
                if (msg != null) {
                    msg.setId(doc.getId());
                }
                messages.add(msg);
            }
            messages.sort(Comparator
                    .comparingLong(this::messageOrder)
                    .thenComparing(message -> message.getCreatedAt() != null ? message.getCreatedAt() : "")
                    .thenComparing(message -> message.getId() != null ? message.getId() : ""));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore findBySessionId interrupted for sessionId={}", sessionId, e);
        } catch (ExecutionException e) {
            log.error("Firestore findBySessionId failed for sessionId={}", sessionId, e);
        }
        return messages;
    }

    public long nextSequence(String sessionId) {
        return findBySessionIdOrderByCreatedAtAsc(sessionId)
                .stream()
                .map(ChatMessage::getSequence)
                .filter(sequence -> sequence != null)
                .max(Long::compareTo)
                .orElse(-1L) + 1L;
    }

    private long messageOrder(ChatMessage message) {
        if (message.getSequence() != null) {
            return message.getSequence();
        }
        return message.getRole() == com.vietnamhistory.chatservice.entity.MessageRole.USER ? Long.MAX_VALUE - 1 : Long.MAX_VALUE;
    }

    public ChatMessage save(ChatMessage message) {
        try {
            if (message.getId() == null) {
                message.setId(java.util.UUID.randomUUID().toString());
            }
            if (message.getCreatedAt() == null) {
                message.setCreatedAt(java.time.LocalDateTime.now().toString());
            }
            getFirestore().collection("chat_messages").document(message.getId()).set(message).get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore save interrupted for message={}", message.getId(), e);
        } catch (ExecutionException e) {
            log.error("Firestore save failed for message={}", message.getId(), e);
        }
        return message;
    }

    public void deleteBySessionId(String sessionId) {
        try {
            var query = getFirestore().collection("chat_messages")
                    .whereEqualTo("sessionId", sessionId)
                    .get().get();
            for (var doc : query.getDocuments()) {
                doc.getReference().delete().get();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore deleteBySessionId interrupted for sessionId={}", sessionId, e);
        } catch (ExecutionException e) {
            log.error("Firestore deleteBySessionId failed for sessionId={}", sessionId, e);
        }
    }
}
