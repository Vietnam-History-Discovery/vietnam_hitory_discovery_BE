package com.vietnamhistory.chatservice;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ChatServiceApplication {

    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(ChatServiceApplication.class);
        app.addInitializers(new DotenvInitializer());
        app.run(args);
    }
}
