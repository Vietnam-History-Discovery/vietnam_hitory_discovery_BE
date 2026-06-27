package com.vietnamhistory.chatservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.Query;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.chatservice.entity.ChatMessage;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;

@Repository
public class ChatMessageRepository {

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
                messages.add(doc.toObject(ChatMessage.class));
            }
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
        return messages;
    }

    public ChatMessage save(ChatMessage message) {
        if (message.getId() == null) {
            message.setId(java.util.UUID.randomUUID().toString());
        }
        getFirestore().collection("chat_messages").document(message.getId()).set(message);
        return message;
    }

    public void deleteBySessionId(String sessionId) {
        try {
            var query = getFirestore().collection("chat_messages")
                    .whereEqualTo("sessionId", sessionId)
                    .get().get();
            for (var doc : query.getDocuments()) {
                doc.getReference().delete();
            }
        } catch (InterruptedException | java.util.concurrent.ExecutionException e) {
            Thread.currentThread().interrupt();
        }
    }
}
