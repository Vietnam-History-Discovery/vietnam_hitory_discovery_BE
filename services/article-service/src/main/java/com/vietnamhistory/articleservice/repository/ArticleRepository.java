package com.vietnamhistory.articleservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.SetOptions;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.articleservice.entity.Article;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ExecutionException;

@Repository
public class ArticleRepository {

    private static final Logger log = LoggerFactory.getLogger(ArticleRepository.class);
    private static final String COLLECTION = "articles";

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public List<Article> findAll() {
        List<Article> articles = new ArrayList<>();
        try {
            var docs = getFirestore().collection(COLLECTION).get().get();
            for (var doc : docs.getDocuments()) {
                Article article = doc.toObject(Article.class);
                if (article != null) {
                    articles.add(article);
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore findAll interrupted", e);
        } catch (ExecutionException e) {
            log.error("Firestore findAll failed", e);
        }
        return articles;
    }

    public Optional<Article> findBySlug(String slug) {
        try {
            var doc = getFirestore().collection(COLLECTION).document(slug).get().get();
            if (doc.exists()) {
                return Optional.ofNullable(doc.toObject(Article.class));
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore findBySlug interrupted for slug={}", slug, e);
        } catch (ExecutionException e) {
            log.error("Firestore findBySlug failed for slug={}", slug, e);
        }
        return Optional.empty();
    }

    public Article save(Article article) {
        try {
            getFirestore().collection(COLLECTION).document(article.getSlug())
                    .set(article, SetOptions.merge()).get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore save interrupted for slug={}", article.getSlug(), e);
        } catch (ExecutionException e) {
            log.error("Firestore save failed for slug={}", article.getSlug(), e);
        }
        return article;
    }

    public void deleteBySlug(String slug) {
        try {
            getFirestore().collection(COLLECTION).document(slug).delete().get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Firestore delete interrupted for slug={}", slug, e);
        } catch (ExecutionException e) {
            log.error("Firestore delete failed for slug={}", slug, e);
        }
    }
}
