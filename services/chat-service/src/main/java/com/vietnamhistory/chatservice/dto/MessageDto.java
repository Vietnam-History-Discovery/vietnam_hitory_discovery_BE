package com.vietnamhistory.chatservice.dto;

import com.vietnamhistory.chatservice.entity.MessageRole;

public record MessageDto(
        String id,
        String sessionId,
        MessageRole role,
        String content,
        String createdAt,
        Long sequence
) {}
