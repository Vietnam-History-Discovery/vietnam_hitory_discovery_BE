package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record TimelineResponse(
        String answer,
        TimelineSnapshotDto timeline,
        @JsonProperty("chunks_used") int chunksUsed,
        List<String> entities,
        @JsonProperty("graph_nodes") int graphNodes
) {}
