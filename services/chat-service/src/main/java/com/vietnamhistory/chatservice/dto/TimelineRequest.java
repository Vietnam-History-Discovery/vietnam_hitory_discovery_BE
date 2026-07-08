package com.vietnamhistory.chatservice.dto;

import jakarta.validation.constraints.NotBlank;

public record TimelineRequest(
        @NotBlank(message = "Question is required")
        String question,
        String context
) {}
