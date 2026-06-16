package com.vietnamhistory.apigateway.filter;

import java.util.Arrays;
import java.util.List;

import org.reactivestreams.Publisher;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.http.server.reactive.ServerHttpResponseDecorator;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;

import jakarta.annotation.PostConstruct;
import reactor.core.publisher.Mono;

@Component
public class CorsFilter implements WebFilter, Ordered {

    @Value("${cors.allowed-origins}")
    private String allowedOriginsConfig;

    private List<String> allowedOrigins;

    @PostConstruct
    public void init() {
        allowedOrigins = Arrays.asList(allowedOriginsConfig.split(","));
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String origin = exchange.getRequest().getHeaders().getOrigin();

        if (HttpMethod.OPTIONS.equals(exchange.getRequest().getMethod())) {
            ServerHttpResponse response = exchange.getResponse();
            response.setStatusCode(HttpStatus.OK);
            applyCorsHeaders(response.getHeaders(), origin);
            return response.setComplete();
        }

        ServerHttpResponseDecorator decorated = new ServerHttpResponseDecorator(exchange.getResponse()) {
            @Override
            public Mono<Void> writeWith(Publisher<? extends DataBuffer> body) {
                applyCorsHeaders(getDelegate().getHeaders(), origin);
                return super.writeWith(body);
            }

            @Override
            public Mono<Void> writeAndFlushWith(Publisher<? extends Publisher<? extends DataBuffer>> body) {
                applyCorsHeaders(getDelegate().getHeaders(), origin);
                return super.writeAndFlushWith(body);
            }
        };

        return chain.filter(exchange.mutate().response(decorated).build());
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }

    private void applyCorsHeaders(HttpHeaders headers, String origin) {
        String allowedOrigin = (origin != null && allowedOrigins.contains(origin))
                ? origin
                : allowedOrigins.get(0);

        headers.remove(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN);
        headers.remove(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS);
        headers.remove(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS);
        headers.remove(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS);
        headers.remove(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS);
        headers.set(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, allowedOrigin);
        headers.set(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, "GET, POST, PUT, DELETE, OPTIONS");
        headers.set(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, "*");
        headers.set(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, "true");
    }
}
