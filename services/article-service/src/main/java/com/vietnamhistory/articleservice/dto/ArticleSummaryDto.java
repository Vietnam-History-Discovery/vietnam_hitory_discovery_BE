package com.vietnamhistory.articleservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record ArticleSummaryDto(
        @JsonProperty("article_id") String articleId,
        String era,
        @JsonProperty("era_slug") String eraSlug,
        @JsonProperty("chapter_num") int chapterNum,
        @JsonProperty("chapter_title") String chapterTitle,
        String slug,
        @JsonProperty("word_count") int wordCount,
        @JsonProperty("estimated_read_minutes") int estimatedReadMinutes,
        List<String> tags
) {}
