package com.vietnamhistory.userservice;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class UserServiceApplication {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(UserServiceApplication.class);
        app.addInitializers(new DotenvInitializer());
        app.run(args);
    }
}
