package com.vietnamhistory.chatservice.controller;

import com.vietnamhistory.chatservice.dto.*;
import com.vietnamhistory.chatservice.entity.SessionType;
import com.vietnamhistory.chatservice.service.ChatService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    @Autowired
    private ChatService chatService;

    @PostMapping("/sessions")
    public ResponseEntity<SessionDto> createSession(
            @RequestBody(required = false) CreateSessionRequest request,
            HttpServletRequest httpRequest) {
        String userId = extractUserId(httpRequest);
        CreateSessionRequest req = request != null ? request : new CreateSessionRequest(null);
        return ResponseEntity.status(HttpStatus.CREATED).body(chatService.createSession(userId, req));
    }

    @GetMapping("/sessions")
    public ResponseEntity<List<SessionDto>> getSessions(
            @RequestParam(required = false) String type,
            HttpServletRequest httpRequest) {
        String userId = extractUserId(httpRequest);
        if (type != null && !type.isBlank()) {
            SessionType sessionType;
            try {
                sessionType = SessionType.valueOf(type.toUpperCase());
            } catch (IllegalArgumentException e) {
                sessionType = null;
            }
            return ResponseEntity.ok(chatService.getUserSessionsByType(userId, sessionType));
        }
        return ResponseEntity.ok(chatService.getUserSessions(userId));
    }

    @GetMapping("/sessions/{id}")
    public ResponseEntity<SessionWithMessagesDto> getSession(
            @PathVariable String id,
            HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.getSession(extractUserId(httpRequest), id));
    }

    @DeleteMapping("/sessions/{id}")
    public ResponseEntity<Void> deleteSession(
            @PathVariable String id,
            HttpServletRequest httpRequest) {
        chatService.deleteSession(extractUserId(httpRequest), id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/sessions/{id}/ask")
    public ResponseEntity<AskResponse> ask(
            @PathVariable String id,
            @Valid @RequestBody AskRequest request,
            HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.ask(extractUserId(httpRequest), id, request));
    }

    @PostMapping("/sessions/{id}/timeline")
    public ResponseEntity<TimelineResponse> askTimeline(
            @PathVariable String id,
            @Valid @RequestBody TimelineRequest request,
            HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.askTimeline(extractUserId(httpRequest), id, request));
    }

    @GetMapping("/sessions/{id}/messages")
    public ResponseEntity<List<MessageDto>> getMessages(
            @PathVariable String id,
            HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.getMessages(extractUserId(httpRequest), id));
    }

    // ─── Helper ──────────────────────────────────────────────────────────────

    private String extractUserId(HttpServletRequest request) {
        String userId = request.getHeader("X-User-Id");
        if (userId == null || userId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "X-User-Id header missing");
        }
        return userId;
    }
}
