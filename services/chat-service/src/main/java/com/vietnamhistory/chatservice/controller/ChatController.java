package com.vietnamhistory.chatservice.controller;

import com.vietnamhistory.chatservice.dto.*;
import com.vietnamhistory.chatservice.service.ChatService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;

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
    public ResponseEntity<List<SessionDto>> getSessions(HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.getUserSessions(extractUserId(httpRequest)));
    }

    @GetMapping("/sessions/{id}")
    public ResponseEntity<SessionWithMessagesDto> getSession(
            @PathVariable UUID id,
            HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.getSession(extractUserId(httpRequest), id));
    }

    @DeleteMapping("/sessions/{id}")
    public ResponseEntity<Void> deleteSession(
            @PathVariable UUID id,
            HttpServletRequest httpRequest) {
        chatService.deleteSession(extractUserId(httpRequest), id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/sessions/{id}/ask")
    public ResponseEntity<AskResponse> ask(
            @PathVariable UUID id,
            @Valid @RequestBody AskRequest request,
            HttpServletRequest httpRequest) {
        return ResponseEntity.ok(chatService.ask(extractUserId(httpRequest), id, request));
    }

    @GetMapping("/sessions/{id}/messages")
    public ResponseEntity<List<MessageDto>> getMessages(
            @PathVariable UUID id,
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
