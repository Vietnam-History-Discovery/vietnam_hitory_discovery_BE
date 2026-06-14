package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiQueryRequest(
        String question,
        @JsonProperty("top_k") int topK
) {}
