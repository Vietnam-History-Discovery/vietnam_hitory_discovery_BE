package com.vietnamhistory.chatservice.service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

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

    @Autowired
    private ChatSessionRepository sessionRepository;

    @Autowired
    private ChatMessageRepository messageRepository;

    @Autowired
    private RestTemplate aiRestTemplate;

    public SessionDto createSession(String userId, CreateSessionRequest request) {
        String title = (request.title() != null && !request.title().isBlank())
                ? request.title()
                : "New Chat";
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle(title);
        return toSessionDto(sessionRepository.save(session));
    }

    public List<SessionDto> getUserSessions(String userId) {
        return sessionRepository.findByUserIdOrderByUpdatedAtDesc(userId)
                .stream()
                .map(this::toSessionDto)
                .collect(Collectors.toList());
    }

    public SessionWithMessagesDto getSession(String userId, String sessionId) {
        ChatSession session = findSessionForUser(userId, sessionId);
        List<MessageDto> messages = messageRepository
                .findBySessionIdOrderByCreatedAtAsc(sessionId)
                .stream()
                .map(this::toMessageDto)
                .collect(Collectors.toList());
        return new SessionWithMessagesDto(toSessionDto(session), messages);
    }

    public void deleteSession(String userId, String sessionId) {
        ChatSession session = findSessionForUser(userId, sessionId);
        messageRepository.deleteBySessionId(sessionId);
        sessionRepository.delete(session);
    }

    public AskResponse ask(String userId, String sessionId, AskRequest request) {
        ChatSession session = findSessionForUser(userId, sessionId);

        String aiQuestion = (request.context() != null && !request.context().isBlank())
                ? "[" + request.context() + "] " + request.question()
                : request.question();

        AiQueryResponse aiResponse = callAiService(aiQuestion);

        ChatMessage userMsg = new ChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setRole(MessageRole.USER);
        userMsg.setContent(request.question());
        messageRepository.save(userMsg);

        ChatMessage assistantMsg = new ChatMessage();
        assistantMsg.setSessionId(sessionId);
        assistantMsg.setRole(MessageRole.ASSISTANT);
        assistantMsg.setContent(aiResponse.answer());
        messageRepository.save(assistantMsg);

        session.setUpdatedAt(LocalDateTime.now().toString());
        sessionRepository.save(session);

        return new AskResponse(aiResponse.answer(), aiResponse.chunksUsed(), aiResponse.entities(), aiResponse.graphNodes());
    }

    public List<MessageDto> getMessages(String userId, String sessionId) {
        findSessionForUser(userId, sessionId);
        return messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId)
                .stream()
                .map(this::toMessageDto)
                .collect(Collectors.toList());
    }

    private AiQueryResponse callAiService(String question) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setAccept(List.of(MediaType.APPLICATION_JSON));

            HttpEntity<AiQueryRequest> entity = new HttpEntity<>(
                    new AiQueryRequest(question, AI_TOP_K), headers);

            AiQueryResponse response = aiRestTemplate.postForObject(
                    "/query", entity, AiQueryResponse.class);

            if (response == null) {
                throw new RuntimeException("AI service returned empty response");
            }
            return response;

        } catch (HttpStatusCodeException e) {
            log.error("AI service HTTP error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new RuntimeException("AI service error: " + e.getStatusCode());
        } catch (Exception e) {
            log.error("AI service call failed: {}", e.getMessage());
            throw new RuntimeException("Failed to reach AI service: " + e.getMessage());
        }
    }

    private ChatSession findSessionForUser(String userId, String sessionId) {
        log.info("findSessionForUser: userId={}, sessionId={}", userId, sessionId);
        var optSession = sessionRepository.findById(sessionId);
        log.info("findSessionForUser: found={}", optSession.isPresent());
        if (optSession.isPresent()) {
            var s = optSession.get();
            log.info("findSessionForUser: session.userId={}, session.id={}", s.getUserId(), s.getId());
        }
        return optSession
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
