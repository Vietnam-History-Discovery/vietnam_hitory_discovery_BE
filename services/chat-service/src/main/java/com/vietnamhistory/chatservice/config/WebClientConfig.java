package com.vietnamhistory.chatservice.config;

import java.time.Duration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class WebClientConfig {

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    @Bean
    public RestTemplate aiRestTemplate(RestTemplateBuilder builder) {
        return builder
                .rootUri(aiServiceUrl)
                .setConnectTimeout(Duration.ofSeconds(5))
                .setReadTimeout(Duration.ofSeconds(30))
                .build();
    }
}
