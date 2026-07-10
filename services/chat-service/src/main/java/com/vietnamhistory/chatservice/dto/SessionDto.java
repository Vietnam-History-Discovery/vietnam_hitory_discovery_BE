package com.vietnamhistory.chatservice.dto;

import com.vietnamhistory.chatservice.entity.SessionType;

public record SessionDto(
        String id,
        String userId,
        String title,
        SessionType sessionType,
        String createdAt,
        String updatedAt
) {}
