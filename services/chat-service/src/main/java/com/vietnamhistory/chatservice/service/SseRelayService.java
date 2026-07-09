package com.vietnamhistory.chatservice.service;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Generic SSE relay — has no knowledge of ChatMessage, sessions, or any
 * specific mode (chat/timeline/future modes). It opens a streaming POST to
 * any URL that responds with an SSE stream, forwards every frame verbatim to
 * an SseEmitter, accumulates "delta" event text, and hands the caller the
 * accumulated text once a "done" frame arrives. A future mode reuses this
 * unchanged — it only needs to supply its own URL, request body, and what to
 * do with the finished text.
 */
@Service
public class SseRelayService {

    private static final Logger log = LoggerFactory.getLogger(SseRelayService.class);

    @Autowired
    private HttpClient sseHttpClient;

    @Autowired
    private ExecutorService sseExecutor;

    @Autowired
    private ObjectMapper objectMapper;

    public SseEmitter relay(
            String url,
            Object requestBody,
            Consumer<String> onComplete,
            BiConsumer<Throwable, SseEmitter> onError) {
        SseEmitter emitter = new SseEmitter(0L);

        sseExecutor.execute(() -> {
            StringBuilder accumulated = new StringBuilder();
            try {
                String jsonBody = objectMapper.writeValueAsString(requestBody);
                log.info("SSE relay POST {} body={}", url, jsonBody);

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(url))
                        .header("Content-Type", "application/json")
                        .header("Accept", "text/event-stream")
                        .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                        .build();

                HttpResponse<Stream<String>> response = sseHttpClient.send(request, HttpResponse.BodyHandlers.ofLines());

                if (response.statusCode() != 200) {
                    String errorBody;
                    try (Stream<String> lines = response.body()) {
                        errorBody = lines.collect(Collectors.joining("\n"));
                    }
                    throw new IOException("Upstream returned HTTP " + response.statusCode() + ": " + errorBody);
                }

                boolean done = false;
                try (Stream<String> lines = response.body()) {
                    String eventName = null;
                    List<String> dataLines = new ArrayList<>();

                    var iterator = lines.iterator();
                    while (iterator.hasNext() && !done) {
                        String line = iterator.next();

                        if (line.isEmpty()) {
                            if (eventName != null && !dataLines.isEmpty()) {
                                String data = String.join("\n", dataLines);
                                emitter.send(SseEmitter.event().name(eventName).data(data));

                                if ("delta".equals(eventName)) {
                                    JsonNode node = objectMapper.readTree(data);
                                    accumulated.append(node.path("text").asText(""));
                                } else if ("done".equals(eventName)) {
                                    done = true;
                                } else if ("error".equals(eventName)) {
                                    emitter.complete();
                                    return;
                                }
                            }
                            eventName = null;
                            dataLines = new ArrayList<>();
                        } else if (line.startsWith("event: ")) {
                            eventName = line.substring(7);
                        } else if (line.startsWith("data: ")) {
                            dataLines.add(line.substring(6));
                        }
                    }
                }

                if (!done) {
                    throw new IOException("Upstream stream ended without a done event");
                }

                emitter.complete();
                onComplete.accept(accumulated.toString());
            } catch (Exception e) {
                log.error("SSE relay failed for {}: {}", url, e.getMessage());
                onError.accept(e, emitter);
            }
        });

        return emitter;
    }
}
