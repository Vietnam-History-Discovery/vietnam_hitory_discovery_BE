package com.vietnamhistory.articleservice.dto;

import java.util.List;

public record ArticleListResponse(
        List<ArticleSummaryDto> articles,
        long total,
        int page,
        int size,
        int totalPages
) {}
