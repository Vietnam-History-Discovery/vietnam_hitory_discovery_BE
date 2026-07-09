package com.vietnamhistory.chatservice.dto;

import com.vietnamhistory.chatservice.entity.MessageRole;
import com.vietnamhistory.chatservice.entity.MessageType;

public record MessageDto(
        String id,
        String sessionId,
        MessageRole role,
        String content,
        MessageType messageType,
        TimelineSnapshotDto timeline,
        String createdAt,
        Long sequence
) {}
