package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record TimelineAiResponse(
        String answer,
        TimelineSnapshotDto timeline,
        @JsonProperty("chunks_used") int chunksUsed,
        java.util.List<String> entities,
        @JsonProperty("graph_nodes") int graphNodes
) {}
