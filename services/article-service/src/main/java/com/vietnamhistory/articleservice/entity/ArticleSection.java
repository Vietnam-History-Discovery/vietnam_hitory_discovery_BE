package com.vietnamhistory.articleservice.entity;

import com.google.cloud.firestore.annotation.PropertyName;

public class ArticleSection {

    private int sectionNum;
    private String sectionTitle;
    private String content;

    public ArticleSection() {}

    @PropertyName("section_num")
    public int getSectionNum() { return sectionNum; }
    @PropertyName("section_num")
    public void setSectionNum(int sectionNum) { this.sectionNum = sectionNum; }

    @PropertyName("section_title")
    public String getSectionTitle() { return sectionTitle; }
    @PropertyName("section_title")
    public void setSectionTitle(String sectionTitle) { this.sectionTitle = sectionTitle; }

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
}
