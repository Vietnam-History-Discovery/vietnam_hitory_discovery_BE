package com.vietnamhistory.articleservice.controller;

import com.vietnamhistory.articleservice.dto.ArticleChatContextDto;
import com.vietnamhistory.articleservice.dto.ArticleDetailDto;
import com.vietnamhistory.articleservice.dto.ArticleListResponse;
import com.vietnamhistory.articleservice.dto.ArticleSummaryDto;
import com.vietnamhistory.articleservice.dto.EraDto;
import com.vietnamhistory.articleservice.service.ArticleService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/articles")
public class ArticleController {

    @Autowired
    private ArticleService articleService;

    @GetMapping
    public ResponseEntity<ArticleListResponse> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String era,
            @RequestParam(required = false) String q) {
        int cappedSize = Math.min(Math.max(size, 1), 20);
        return ResponseEntity.ok(articleService.list(Math.max(page, 0), cappedSize, era, q));
    }

    @GetMapping("/eras")
    public ResponseEntity<List<EraDto>> listEras() {
        return ResponseEntity.ok(articleService.listEras());
    }

    @GetMapping("/era/{eraSlug}")
    public ResponseEntity<List<ArticleSummaryDto>> listByEra(@PathVariable String eraSlug) {
        return ResponseEntity.ok(articleService.listByEra(eraSlug));
    }

    @GetMapping("/{slug}")
    public ResponseEntity<ArticleDetailDto> getBySlug(@PathVariable String slug) {
        return ResponseEntity.ok(articleService.getBySlug(slug));
    }

    @GetMapping("/{slug}/chat-context")
    public ResponseEntity<ArticleChatContextDto> getChatContext(@PathVariable String slug) {
        return ResponseEntity.ok(articleService.getChatContext(slug));
    }

    @PostMapping
    public ResponseEntity<ArticleDetailDto> create(
            @RequestHeader(value = "X-User-Role", required = false) String role,
            @Valid @RequestBody ArticleDetailDto dto) {
        requireAdmin(role);
        return ResponseEntity.status(HttpStatus.CREATED).body(articleService.create(dto));
    }

    @PutMapping("/{slug}")
    public ResponseEntity<ArticleDetailDto> update(
            @PathVariable String slug,
            @RequestHeader(value = "X-User-Role", required = false) String role,
            @Valid @RequestBody ArticleDetailDto dto) {
        requireAdmin(role);
        return ResponseEntity.ok(articleService.update(slug, dto));
    }

    @DeleteMapping("/{slug}")
    public ResponseEntity<Void> delete(
            @PathVariable String slug,
            @RequestHeader(value = "X-User-Role", required = false) String role) {
        requireAdmin(role);
        articleService.delete(slug);
        return ResponseEntity.noContent().build();
    }

    private void requireAdmin(String role) {
        if (!"admin".equals(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Admin role required");
        }
    }
}
