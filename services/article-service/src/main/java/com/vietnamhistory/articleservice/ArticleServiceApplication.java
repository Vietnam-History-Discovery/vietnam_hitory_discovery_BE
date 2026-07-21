package com.vietnamhistory.articleservice;

import com.google.firebase.FirebaseApp;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import javax.annotation.PostConstruct;

@SpringBootApplication
public class ArticleServiceApplication {

    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(ArticleServiceApplication.class);
        app.addInitializers(new DotenvInitializer());
        app.run(args);
    }

    @PostConstruct
    public void initializeFirebase() {
        if (FirebaseApp.getApps().isEmpty()) {
            FirebaseApp.initializeApp();
        }
    }
}
