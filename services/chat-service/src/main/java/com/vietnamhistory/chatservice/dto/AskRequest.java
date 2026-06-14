package com.vietnamhistory.chatservice.dto;

import jakarta.validation.constraints.NotBlank;

public record AskRequest(
        @NotBlank(message = "Question is required")
        String question,

        String context
) {}
