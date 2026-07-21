package com.vietnamhistory.chatservice.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiQueryRequest(
        String question,
        @JsonProperty("top_k") int topK,
        List<ConversationTurn> history
) {
    public AiQueryRequest(String question, int topK) {
        this(question, topK, List.of());
    }

    public record ConversationTurn(String role, String content) {}
}
