package com.vietnamhistory.chatservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.Query;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.chatservice.entity.ChatMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
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
                    .orderBy("createdAt", Query.Direction.ASCENDING)
                    .get().get();
            for (var doc : query.getDocuments()) {
                ChatMessage msg = doc.toObject(ChatMessage.class);
                if (msg != null) {
                    msg.setId(doc.getId());
                }
                messages.add(msg);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore findBySessionId interrupted for sessionId={}", sessionId, e);
        } catch (ExecutionException e) {
            log.error("Firestore findBySessionId failed for sessionId={}", sessionId, e);
        }
        return messages;
    }

    public ChatMessage save(ChatMessage message) {
        try {
            if (message.getId() == null) {
                message.setId(java.util.UUID.randomUUID().toString());
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
