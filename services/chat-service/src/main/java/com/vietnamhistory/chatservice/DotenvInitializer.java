package com.vietnamhistory.chatservice;

import io.github.cdimascio.dotenv.Dotenv;
import org.springframework.context.ApplicationContextInitializer;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.MapPropertySource;

import java.util.HashMap;
import java.util.Map;

public class DotenvInitializer implements ApplicationContextInitializer<ConfigurableApplicationContext> {
    @Override
    public void initialize(ConfigurableApplicationContext ctx) {
        Dotenv dotenv = Dotenv.configure()
                .directory("../../")
                .ignoreIfMissing()
                .load();

        Map<String, Object> props = new HashMap<>();
        dotenv.entries().forEach(e -> {
            props.put(e.getKey(), e.getValue());
            System.setProperty(e.getKey(), e.getValue()); // also set as system property
        });

        ctx.getEnvironment().getPropertySources()
                .addFirst(new MapPropertySource("dotenv", props));
    }
}