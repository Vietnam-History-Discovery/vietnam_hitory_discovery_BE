package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record TimelineSnapshotDto(
        String id,
        String title,
        @JsonProperty("events") List<TimelineEventDto> events
) {}
