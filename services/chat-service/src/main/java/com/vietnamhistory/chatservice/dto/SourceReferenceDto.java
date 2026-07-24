package com.vietnamhistory.chatservice.dto;

public class SourceReferenceDto {

    private String document;
    private String url;

    public SourceReferenceDto() {}

    public SourceReferenceDto(String document, String url) {
        this.document = document;
        this.url = url;
    }

    public String getDocument() { return document; }
    public void setDocument(String document) { this.document = document; }

    public String getUrl() { return url; }
    public void setUrl(String url) { this.url = url; }
}
