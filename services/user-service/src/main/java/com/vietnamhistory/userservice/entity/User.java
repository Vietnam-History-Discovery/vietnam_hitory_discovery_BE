package com.vietnamhistory.userservice.entity;

import java.time.LocalDateTime;

public class User {

    private String id;
    private String username;
    private String email;
    private Role role = Role.USER;
    private UserStatus status = UserStatus.ACTIVE;
    private String statusReason;
    private String createdAt;

    public User() {}

    public User(String id, String username, String email) {
        this.id = id;
        this.username = username;
        this.email = email;
        this.createdAt = LocalDateTime.now().toString();
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public Role getRole() { return role; }
    public void setRole(Role role) { this.role = role; }

    public UserStatus getStatus() { return status; }
    public void setStatus(UserStatus status) { this.status = status; }

    public String getStatusReason() { return statusReason; }
    public void setStatusReason(String statusReason) { this.statusReason = statusReason; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }
}
