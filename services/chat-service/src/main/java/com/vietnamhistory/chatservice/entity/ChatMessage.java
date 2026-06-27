package com.vietnamhistory.chatservice.entity;

import java.time.LocalDateTime;

public class ChatMessage {

    private String id;
    private String sessionId;
    private MessageRole role;
    private String content;
    private String createdAt;

    public ChatMessage() {}

    public ChatMessage(String id, String sessionId, MessageRole role, String content) {
        this.id = id;
        this.sessionId = sessionId;
        this.role = role;
        this.content = content;
        this.createdAt = LocalDateTime.now().toString();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public MessageRole getRole() { return role; }
    public void setRole(MessageRole role) { this.role = role; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
}
