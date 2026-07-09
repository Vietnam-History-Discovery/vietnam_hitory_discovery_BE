package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record TimelineEventDto(
        String id,
        String dateLabel,
        @JsonProperty("start_year") Integer startYear,
        @JsonProperty("end_year") Integer endYear,
        String title,
        String description,
        @JsonProperty("related_entities") java.util.List<String> relatedEntities
) {}
