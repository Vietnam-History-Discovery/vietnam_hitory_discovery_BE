package com.vietnamhistory.chatservice.dto;

import com.vietnamhistory.chatservice.entity.MessageRole;

import java.time.LocalDateTime;
import java.util.UUID;

public record MessageDto(
        UUID id,
        UUID sessionId,
        MessageRole role,
        String content,
        LocalDateTime createdAt
) {}
