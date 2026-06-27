package com.vietnamhistory.chatservice.entity;

import java.time.LocalDateTime;

public class ChatSession {

    private String id;
    private String userId;
    private String title;
    private String createdAt;
    private String updatedAt;

    public ChatSession() {}

    public ChatSession(String id, String userId, String title) {
        this.id = id;
        this.userId = userId;
        this.title = title;
        this.createdAt = LocalDateTime.now().toString();
        this.updatedAt = this.createdAt;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }
}
