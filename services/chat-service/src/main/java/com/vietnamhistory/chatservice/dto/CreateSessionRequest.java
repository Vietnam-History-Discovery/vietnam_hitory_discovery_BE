package com.vietnamhistory.chatservice.dto;

import com.vietnamhistory.chatservice.entity.SessionType;

public record CreateSessionRequest(String title, SessionType type) {
    public CreateSessionRequest { if (type == null) type = SessionType.CHAT; }
    public CreateSessionRequest(String title) { this(title, SessionType.CHAT); }
}
