package com.vietnamhistory.chatservice.dto;

import java.time.LocalDateTime;
import java.util.UUID;

public record SessionDto(
        UUID id,
        String userId,
        String title,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {}
