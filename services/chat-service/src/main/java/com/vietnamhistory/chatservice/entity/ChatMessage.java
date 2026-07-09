package com.vietnamhistory.chatservice.entity;

import java.time.LocalDateTime;

public class ChatMessage {

    private String id;
    private String sessionId;
    private MessageRole role;
    private String content;
    private MessageType messageType;
    private String timeline;
    private String createdAt;
    private Long sequence;

    public ChatMessage() {
        this.messageType = MessageType.TEXT;
    }

    public ChatMessage(String id, String sessionId, MessageRole role, String content) {
        this.id = id;
        this.sessionId = sessionId;
        this.role = role;
        this.content = content;
        this.messageType = MessageType.TEXT;
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

    public MessageType getMessageType() { return messageType; }
    public void setMessageType(MessageType messageType) { this.messageType = messageType; }

    public String getTimeline() { return timeline; }
    public void setTimeline(String timeline) { this.timeline = timeline; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public Long getSequence() { return sequence; }
    public void setSequence(Long sequence) { this.sequence = sequence; }
}
