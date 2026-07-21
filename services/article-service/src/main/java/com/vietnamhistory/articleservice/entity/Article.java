package com.vietnamhistory.articleservice.entity;

import com.google.cloud.firestore.annotation.PropertyName;

import java.util.List;

public class Article {

    private String articleId;
    private String source;
    private String era;
    private String eraSlug;
    private int chapterNum;
    private String chapterTitle;
    private String slug;
    private String content;
    private List<ArticleSection> sections;
    private int wordCount;
    private int estimatedReadMinutes;
    private List<String> tags;

    public Article() {}

    @PropertyName("article_id")
    public String getArticleId() { return articleId; }
    @PropertyName("article_id")
    public void setArticleId(String articleId) { this.articleId = articleId; }

    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }

    public String getEra() { return era; }
    public void setEra(String era) { this.era = era; }

    @PropertyName("era_slug")
    public String getEraSlug() { return eraSlug; }
    @PropertyName("era_slug")
    public void setEraSlug(String eraSlug) { this.eraSlug = eraSlug; }

    @PropertyName("chapter_num")
    public int getChapterNum() { return chapterNum; }
    @PropertyName("chapter_num")
    public void setChapterNum(int chapterNum) { this.chapterNum = chapterNum; }

    @PropertyName("chapter_title")
    public String getChapterTitle() { return chapterTitle; }
    @PropertyName("chapter_title")
    public void setChapterTitle(String chapterTitle) { this.chapterTitle = chapterTitle; }

    public String getSlug() { return slug; }
    public void setSlug(String slug) { this.slug = slug; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }

    public List<ArticleSection> getSections() { return sections; }
    public void setSections(List<ArticleSection> sections) { this.sections = sections; }

    @PropertyName("word_count")
    public int getWordCount() { return wordCount; }
    @PropertyName("word_count")
    public void setWordCount(int wordCount) { this.wordCount = wordCount; }

    @PropertyName("estimated_read_minutes")
    public int getEstimatedReadMinutes() { return estimatedReadMinutes; }
    @PropertyName("estimated_read_minutes")
    public void setEstimatedReadMinutes(int estimatedReadMinutes) { this.estimatedReadMinutes = estimatedReadMinutes; }

    public List<String> getTags() { return tags; }
    public void setTags(List<String> tags) { this.tags = tags; }
}
