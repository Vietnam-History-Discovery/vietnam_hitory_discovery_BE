package com.vietnamhistory.apigateway.filter;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.ExecutionException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;

import com.google.cloud.firestore.Firestore;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.google.firebase.auth.FirebaseToken;
import com.google.firebase.cloud.FirestoreClient;

import reactor.core.publisher.Mono;

@Component
public class JwtAuthFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthFilter.class);

    // Paths that bypass JWT validation entirely
    private static final List<String> PUBLIC_PREFIXES = List.of("/api/auth/");

    // Paths that are public for read (GET) requests only — writes still require a valid token
    private static final List<String> PUBLIC_GET_PREFIXES = List.of("/api/articles");

    @Override
    public int getOrder() {
        return -1; // run before other filters
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();

        // Skip auth for public paths, public GET reads, and CORS preflight
        if (isPublicPath(path) || isPublicGetRequest(path, request.getMethod()) || isPreflightRequest(request)) {
            return chain.filter(exchange);
        }

        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            log.debug("Missing Bearer token for path: {}", path);
            return sendUnauthorized(exchange, "Missing or invalid Authorization header");
        }

        String token = authHeader.substring(7);

        try {
            FirebaseToken decodedToken = FirebaseAuth.getInstance().verifyIdToken(token);
            String email = decodedToken.getEmail();
            String uid = decodedToken.getUid();
            String role = lookupRole(uid);

            ServerHttpRequest mutatedRequest = request.mutate()
                    .headers(h -> {
                        h.remove("X-User-Email");
                        h.remove("X-User-Id");
                        h.remove("X-User-Role");
                        h.set("X-User-Email", email != null ? email : "");
                        h.set("X-User-Id", uid);
                        h.set("X-User-Role", role);
                    })
                    .build();

            log.debug("JWT valid for uid {} (role={}); forwarding to {}", uid, role, path);
            return chain.filter(exchange.mutate().request(mutatedRequest).build());

        } catch (FirebaseAuthException e) {
            log.debug("JWT validation failed: {}", e.getMessage());
            return sendUnauthorized(exchange, "Invalid or expired token");
        }
    }

    private String lookupRole(String uid) {
        try {
            Firestore db = FirestoreClient.getFirestore();
            var doc = db.collection("users").document(uid).get().get();
            if (doc.exists()) {
                String role = doc.getString("role");
                if (role != null && !role.isBlank()) {
                    return role.toLowerCase();
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (ExecutionException e) {
            log.warn("Failed to look up role for uid {}: {}", uid, e.getMessage());
        }
        return "user";
    }

    private boolean isPublicPath(String path) {
        return PUBLIC_PREFIXES.stream().anyMatch(path::startsWith);
    }

    private boolean isPublicGetRequest(String path, HttpMethod method) {
        return HttpMethod.GET.equals(method) && PUBLIC_GET_PREFIXES.stream().anyMatch(path::startsWith);
    }

    private boolean isPreflightRequest(ServerHttpRequest request) {
        return HttpMethod.OPTIONS.equals(request.getMethod());
    }

    private Mono<Void> sendUnauthorized(ServerWebExchange exchange, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        String body = String.format("{\"error\":\"Unauthorized\",\"message\":\"%s\"}", message);
        DataBuffer buffer = response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }
}
