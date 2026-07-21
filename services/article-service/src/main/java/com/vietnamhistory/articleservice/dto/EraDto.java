package com.vietnamhistory.articleservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record EraDto(
        String era,
        @JsonProperty("era_slug") String eraSlug,
        long count
) {}
