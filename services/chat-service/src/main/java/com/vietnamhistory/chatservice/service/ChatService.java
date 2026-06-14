package com.vietnamhistory.chatservice.service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import com.vietnamhistory.chatservice.dto.AiQueryRequest;
import com.vietnamhistory.chatservice.dto.AiQueryResponse;
import com.vietnamhistory.chatservice.dto.AskRequest;
import com.vietnamhistory.chatservice.dto.AskResponse;
import com.vietnamhistory.chatservice.dto.CreateSessionRequest;
import com.vietnamhistory.chatservice.dto.MessageDto;
import com.vietnamhistory.chatservice.dto.SessionDto;
import com.vietnamhistory.chatservice.dto.SessionWithMessagesDto;
import com.vietnamhistory.chatservice.entity.ChatMessage;
import com.vietnamhistory.chatservice.entity.ChatSession;
import com.vietnamhistory.chatservice.entity.MessageRole;
import com.vietnamhistory.chatservice.repository.ChatMessageRepository;
import com.vietnamhistory.chatservice.repository.ChatSessionRepository;

@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);
    private static final int AI_TOP_K = 10;
    private static final Duration AI_TIMEOUT = Duration.ofSeconds(30);

    @Autowired
    private ChatSessionRepository sessionRepository;

    @Autowired
    private ChatMessageRepository messageRepository;

    @Autowired
    private WebClient aiWebClient;

    @Transactional
    public SessionDto createSession(String userId, CreateSessionRequest request) {
        String title = (request.title() != null && !request.title().isBlank())
                ? request.title()
                : "New Chat";
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle(title);
        return toSessionDto(sessionRepository.save(session));
    }

    @Transactional(readOnly = true)
    public List<SessionDto> getUserSessions(String userId) {
        return sessionRepository.findByUserIdOrderByUpdatedAtDesc(userId)
                .stream()
                .map(this::toSessionDto)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public SessionWithMessagesDto getSession(String userId, UUID sessionId) {
        ChatSession session = findSessionForUser(userId, sessionId);
        List<MessageDto> messages = messageRepository
                .findBySessionIdOrderByCreatedAtAsc(sessionId)
                .stream()
                .map(this::toMessageDto)
                .collect(Collectors.toList());
        return new SessionWithMessagesDto(toSessionDto(session), messages);
    }

    @Transactional
    public void deleteSession(String userId, UUID sessionId) {
        ChatSession session = findSessionForUser(userId, sessionId);
        messageRepository.deleteBySessionId(sessionId);
        sessionRepository.delete(session);
    }

    @Transactional
    public AskResponse ask(String userId, UUID sessionId, AskRequest request) {
        ChatSession session = findSessionForUser(userId, sessionId);

        // Prepend optional context before sending to AI
        String aiQuestion = (request.context() != null && !request.context().isBlank())
                ? "[" + request.context() + "] " + request.question()
                : request.question();

        // Call AI service — block() is acceptable in a servlet thread
        AiQueryResponse aiResponse = callAiService(aiQuestion);

        // Persist user message (original question, without injected context)
        ChatMessage userMsg = new ChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setRole(MessageRole.USER);
        userMsg.setContent(request.question());
        messageRepository.save(userMsg);

        // Persist assistant reply
        ChatMessage assistantMsg = new ChatMessage();
        assistantMsg.setSessionId(sessionId);
        assistantMsg.setRole(MessageRole.ASSISTANT);
        assistantMsg.setContent(aiResponse.answer());
        messageRepository.save(assistantMsg);

        // Touch session so it bubbles to the top of the list
        session.setUpdatedAt(LocalDateTime.now());
        sessionRepository.save(session);

        return new AskResponse(aiResponse.answer(), aiResponse.chunksUsed(), aiResponse.entities(), aiResponse.graphNodes());
    }

    @Transactional(readOnly = true)
    public List<MessageDto> getMessages(String userId, UUID sessionId) {
        findSessionForUser(userId, sessionId);
        return messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId)
                .stream()
                .map(this::toMessageDto)
                .collect(Collectors.toList());
    }

    // ─── Helpers ─────────────────────────────────────────────────────────────

    private AiQueryResponse callAiService(String question) {
        try {
            AiQueryResponse response = aiWebClient.post()
                    .uri("/query")
                    .bodyValue(new AiQueryRequest(question, AI_TOP_K))
                    .retrieve()
                    .bodyToMono(AiQueryResponse.class)
                    .timeout(AI_TIMEOUT)
                    .block();

            if (response == null) {
                throw new RuntimeException("AI service returned empty response");
            }
            return response;

        } catch (WebClientResponseException e) {
            log.error("AI service HTTP error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new RuntimeException("AI service error: " + e.getStatusCode());
        } catch (Exception e) {
            log.error("AI service call failed: {}", e.getMessage());
            throw new RuntimeException("Failed to reach AI service: " + e.getMessage());
        }
    }

    private ChatSession findSessionForUser(String userId, UUID sessionId) {
        return sessionRepository.findById(sessionId)
                .filter(s -> s.getUserId().equals(userId))
                .orElseThrow(() -> new RuntimeException("Session not found"));
    }

    private SessionDto toSessionDto(ChatSession s) {
        return new SessionDto(s.getId(), s.getUserId(), s.getTitle(), s.getCreatedAt(), s.getUpdatedAt());
    }

    private MessageDto toMessageDto(ChatMessage m) {
        return new MessageDto(m.getId(), m.getSessionId(), m.getRole(), m.getContent(), m.getCreatedAt());
    }
}
