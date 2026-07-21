package com.vietnamhistory.articleservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record ArticleDetailDto(
        @JsonProperty("article_id") @NotBlank String articleId,
        String source,
        String era,
        @JsonProperty("era_slug") String eraSlug,
        @JsonProperty("chapter_num") int chapterNum,
        @JsonProperty("chapter_title") @NotBlank String chapterTitle,
        @NotBlank String slug,
        String content,
        List<ArticleSectionDto> sections,
        @JsonProperty("word_count") int wordCount,
        @JsonProperty("estimated_read_minutes") int estimatedReadMinutes,
        List<String> tags
) {}
