package com.vietnamhistory.chatservice.dto;

public record SessionDto(
        String id,
        String userId,
        String title,
        String createdAt,
        String updatedAt
) {}
