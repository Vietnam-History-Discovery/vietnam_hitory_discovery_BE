package com.vietnamhistory.articleservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ArticleSectionDto(
        @JsonProperty("section_num") int sectionNum,
        @JsonProperty("section_title") String sectionTitle,
        String content
) {}
