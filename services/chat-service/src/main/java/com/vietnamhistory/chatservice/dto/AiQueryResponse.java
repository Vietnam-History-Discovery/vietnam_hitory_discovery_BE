package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record AiQueryResponse(
        String answer,
        @JsonProperty("chunks_used") int chunksUsed,
        List<String> entities,
        @JsonProperty("graph_nodes") int graphNodes,
        List<SourceReferenceDto> sources
) {}
