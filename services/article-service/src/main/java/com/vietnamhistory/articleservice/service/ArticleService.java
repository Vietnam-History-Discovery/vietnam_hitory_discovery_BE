package com.vietnamhistory.articleservice.service;

import com.vietnamhistory.articleservice.dto.ArticleChatContextDto;
import com.vietnamhistory.articleservice.dto.ArticleDetailDto;
import com.vietnamhistory.articleservice.dto.ArticleListResponse;
import com.vietnamhistory.articleservice.dto.ArticleSectionDto;
import com.vietnamhistory.articleservice.dto.ArticleSummaryDto;
import com.vietnamhistory.articleservice.dto.EraDto;
import com.vietnamhistory.articleservice.entity.Article;
import com.vietnamhistory.articleservice.entity.ArticleSection;
import com.vietnamhistory.articleservice.repository.ArticleRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class ArticleService {

    // Fixed chronological order of Việt Nam Sử Lược's parts — not derivable from any Firestore field.
    private static final List<String> ERA_ORDER = List.of(
            "mo-dau", "thuong-co", "bac-thuoc", "tu-chu", "tu-chu-nam-bac", "can-kim"
    );

    private static final int CHAT_CONTEXT_CONTENT_CHARS = 800;
    private static final int CHAT_CONTEXT_SECTION_CHARS = 250;
    private static final int CHAT_CONTEXT_MAX_SECTIONS = 3;

    @Autowired
    private ArticleRepository articleRepository;

    private volatile List<Article> cache = new ArrayList<>();

    @PostConstruct
    public void loadCache() {
        cache = articleRepository.findAll();
    }

    public ArticleListResponse list(int page, int size, String era, String q) {
        String query = (q == null || q.isBlank()) ? null : q.trim().toLowerCase();

        List<Article> filtered = cache.stream()
                .filter(a -> era == null || era.isBlank() || era.equals(a.getEraSlug()))
                .filter(a -> query == null || matchesQuery(a, query))
                .sorted(Comparator.comparing(Article::getEraSlug, Comparator.comparingInt(this::eraOrderIndex))
                        .thenComparingInt(Article::getChapterNum))
                .toList();

        int total = filtered.size();
        int start = Math.min(page * size, total);
        int end = Math.min(start + size, total);
        List<ArticleSummaryDto> paged = filtered.subList(start, end).stream()
                .map(this::toSummary)
                .toList();

        int totalPages = size == 0 ? 0 : (int) Math.ceil((double) total / size);
        return new ArticleListResponse(paged, total, page, size, totalPages);
    }

    private boolean matchesQuery(Article a, String q) {
        if (a.getChapterTitle() != null && a.getChapterTitle().toLowerCase().contains(q)) {
            return true;
        }
        if (a.getTags() != null && a.getTags().stream().anyMatch(t -> t.toLowerCase().contains(q))) {
            return true;
        }
        if (a.getContent() != null) {
            String snippet = a.getContent().substring(0, Math.min(500, a.getContent().length()));
            if (snippet.toLowerCase().contains(q)) {
                return true;
            }
        }
        return false;
    }

    public ArticleDetailDto getBySlug(String slug) {
        return toDetail(findBySlugOrThrow(slug));
    }

    /**
     * Rich, article-specific context string for the chat AI — mirrors the Dynasty
     * chat-context endpoint so RAG retrieval is grounded in the actual article
     * being read instead of a coarse era label (see ChatService.askStream, which
     * wraps this in "[" + context + "]" before the question).
     */
    public ArticleChatContextDto getChatContext(String slug) {
        Article a = findBySlugOrThrow(slug);

        StringBuilder sb = new StringBuilder();
        sb.append("=== Bài viết: ").append(a.getChapterTitle()).append(" ===\n");
        if (a.getEra() != null && !a.getEra().isBlank()) {
            sb.append("Thời kỳ: ").append(a.getEra()).append("\n");
        }
        if (a.getTags() != null && !a.getTags().isEmpty()) {
            sb.append("Chủ đề: ").append(String.join(", ", a.getTags())).append("\n");
        }
        sb.append("\nNội dung:\n");

        List<ArticleSection> sections = a.getSections();
        if (sections != null && !sections.isEmpty()) {
            sections.stream().limit(CHAT_CONTEXT_MAX_SECTIONS).forEach(s ->
                    sb.append(s.getSectionTitle()).append(": ")
                            .append(truncate(s.getContent(), CHAT_CONTEXT_SECTION_CHARS)).append("\n"));
        } else {
            sb.append(truncate(a.getContent(), CHAT_CONTEXT_CONTENT_CHARS)).append("\n");
        }

        // Strip "]" so the "[" + context + "]" wrapper downstream can't be truncated early.
        String context = sb.toString().replace("]", ")");
        return new ArticleChatContextDto(slug, context);
    }

    private static String truncate(String text, int maxChars) {
        if (text == null) return "";
        String trimmed = text.strip();
        if (trimmed.length() <= maxChars) return trimmed;
        return trimmed.substring(0, maxChars) + "…";
    }

    public List<ArticleSummaryDto> listByEra(String eraSlug) {
        return cache.stream()
                .filter(a -> eraSlug.equals(a.getEraSlug()))
                .sorted(Comparator.comparingInt(Article::getChapterNum))
                .map(this::toSummary)
                .toList();
    }

    public List<EraDto> listEras() {
        Map<String, long[]> counts = new LinkedHashMap<>();
        Map<String, String> eraNames = new LinkedHashMap<>();
        for (Article a : cache) {
            counts.computeIfAbsent(a.getEraSlug(), k -> new long[1])[0]++;
            eraNames.putIfAbsent(a.getEraSlug(), a.getEra());
        }
        return counts.entrySet().stream()
                .sorted(Comparator.comparingInt(e -> eraOrderIndex(e.getKey())))
                .map(e -> new EraDto(eraNames.get(e.getKey()), e.getKey(), e.getValue()[0]))
                .toList();
    }

    public ArticleDetailDto create(ArticleDetailDto dto) {
        if (findBySlug(dto.slug()).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Article already exists: " + dto.slug());
        }
        Article article = toEntity(dto);
        articleRepository.save(article);
        loadCache();
        return toDetail(article);
    }

    public ArticleDetailDto update(String slug, ArticleDetailDto dto) {
        findBySlugOrThrow(slug);
        Article article = toEntity(dto);
        article.setSlug(slug);
        articleRepository.save(article);
        loadCache();
        return toDetail(article);
    }

    public void delete(String slug) {
        findBySlugOrThrow(slug);
        articleRepository.deleteBySlug(slug);
        loadCache();
    }

    private int eraOrderIndex(String eraSlug) {
        int idx = ERA_ORDER.indexOf(eraSlug);
        return idx == -1 ? ERA_ORDER.size() : idx;
    }

    private java.util.Optional<Article> findBySlug(String slug) {
        return cache.stream().filter(a -> slug.equals(a.getSlug())).findFirst();
    }

    private Article findBySlugOrThrow(String slug) {
        return findBySlug(slug)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Article not found: " + slug));
    }

    private ArticleSummaryDto toSummary(Article a) {
        return new ArticleSummaryDto(a.getArticleId(), a.getEra(), a.getEraSlug(), a.getChapterNum(),
                a.getChapterTitle(), a.getSlug(), a.getWordCount(), a.getEstimatedReadMinutes(), a.getTags());
    }

    private ArticleDetailDto toDetail(Article a) {
        List<ArticleSectionDto> sections = a.getSections() == null ? List.of() :
                a.getSections().stream()
                        .map(s -> new ArticleSectionDto(s.getSectionNum(), s.getSectionTitle(), s.getContent()))
                        .toList();
        return new ArticleDetailDto(a.getArticleId(), a.getSource(), a.getEra(), a.getEraSlug(), a.getChapterNum(),
                a.getChapterTitle(), a.getSlug(), a.getContent(), sections, a.getWordCount(),
                a.getEstimatedReadMinutes(), a.getTags());
    }

    private Article toEntity(ArticleDetailDto dto) {
        Article article = new Article();
        article.setArticleId(dto.articleId());
        article.setSource(dto.source());
        article.setEra(dto.era());
        article.setEraSlug(dto.eraSlug());
        article.setChapterNum(dto.chapterNum());
        article.setChapterTitle(dto.chapterTitle());
        article.setSlug(dto.slug());
        article.setContent(dto.content());
        article.setSections(dto.sections() == null ? List.of() :
                dto.sections().stream().map(this::toSectionEntity).toList());
        article.setWordCount(dto.wordCount());
        article.setEstimatedReadMinutes(dto.estimatedReadMinutes());
        article.setTags(dto.tags());
        return article;
    }

    private ArticleSection toSectionEntity(ArticleSectionDto dto) {
        ArticleSection section = new ArticleSection();
        section.setSectionNum(dto.sectionNum());
        section.setSectionTitle(dto.sectionTitle());
        section.setContent(dto.content());
        return section;
    }
}
