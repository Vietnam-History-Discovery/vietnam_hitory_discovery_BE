package com.vietnamhistory.chatservice.service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.vietnamhistory.chatservice.dto.AiQueryRequest;
import com.vietnamhistory.chatservice.dto.AiQueryResponse;
import com.vietnamhistory.chatservice.dto.AskRequest;
import com.vietnamhistory.chatservice.dto.AskResponse;
import com.vietnamhistory.chatservice.dto.CreateSessionRequest;
import com.vietnamhistory.chatservice.dto.MessageDto;
import com.vietnamhistory.chatservice.dto.SessionDto;
import com.vietnamhistory.chatservice.dto.SessionWithMessagesDto;
import com.vietnamhistory.chatservice.dto.TimelineAiRequest;
import com.vietnamhistory.chatservice.dto.TimelineAiRequest.RecentExchange;
import com.vietnamhistory.chatservice.dto.TimelineRequest;
import com.vietnamhistory.chatservice.dto.TimelineSnapshotDto;
import com.vietnamhistory.chatservice.entity.ChatMessage;
import com.vietnamhistory.chatservice.entity.ChatSession;
import com.vietnamhistory.chatservice.entity.MessageRole;
import com.vietnamhistory.chatservice.entity.MessageType;
import com.vietnamhistory.chatservice.entity.SessionType;
import com.vietnamhistory.chatservice.repository.ChatMessageRepository;
import com.vietnamhistory.chatservice.repository.ChatSessionRepository;

@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);
    private static final int AI_TOP_K = 10;
    private static final int HISTORY_MAX_MESSAGES = 6; // 3 exchanges
    private static final int HISTORY_CONTENT_MAX_CHARS = 200;

    @Autowired
    private ChatSessionRepository sessionRepository;

    @Autowired
    private ChatMessageRepository messageRepository;

    @Autowired
    private RestTemplate aiRestTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private SseRelayService sseRelay;

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    public SessionDto createSession(String userId, CreateSessionRequest request) {
        String title = (request.title() != null && !request.title().isBlank())
                ? request.title()
                : "New Chat";
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle(title);
        session.setSessionType(request.type() != null ? request.type() : SessionType.CHAT);
        return toSessionDto(sessionRepository.save(session));
    }

    public List<SessionDto> getUserSessions(String userId) {
        return getUserSessionsByType(userId, null);
    }

    public List<SessionDto> getUserSessionsByType(String userId, SessionType type) {
        return sessionRepository.findByUserIdAndTypeOrderByUpdatedAtDesc(userId, type)
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
        long nextSequence = messageRepository.nextSequence(sessionId);

        ChatMessage userMsg = new ChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setRole(MessageRole.USER);
        userMsg.setContent(request.question());
        userMsg.setSequence(nextSequence);
        messageRepository.save(userMsg);

        session.setUpdatedAt(LocalDateTime.now().toString());
        sessionRepository.save(session);

        AiQueryResponse aiResponse = callAiService(aiQuestion);

        ChatMessage assistantMsg = new ChatMessage();
        assistantMsg.setSessionId(sessionId);
        assistantMsg.setRole(MessageRole.ASSISTANT);
        assistantMsg.setContent(aiResponse.answer());
        assistantMsg.setSequence(nextSequence + 1);
        messageRepository.save(assistantMsg);

        session.setUpdatedAt(LocalDateTime.now().toString());
        sessionRepository.save(session);

        return new AskResponse(aiResponse.answer(), aiResponse.chunksUsed(), aiResponse.entities(), aiResponse.graphNodes());
    }

    public SseEmitter askStream(String userId, String sessionId, AskRequest request) {
        ChatSession session = findSessionForUser(userId, sessionId);

        String aiQuestion = (request.context() != null && !request.context().isBlank())
                ? "[" + request.context() + "] " + request.question()
                : request.question();
        long nextSequence = messageRepository.nextSequence(sessionId);

        // Snapshot conversation history before persisting the new question so
        // it isn't duplicated in the history payload.
        List<AiQueryRequest.ConversationTurn> history = buildConversationHistory(sessionId);

        ChatMessage userMsg = new ChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setRole(MessageRole.USER);
        userMsg.setContent(request.question());
        userMsg.setSequence(nextSequence);
        messageRepository.save(userMsg);

        session.setUpdatedAt(LocalDateTime.now().toString());
        sessionRepository.save(session);

        return sseRelay.relay(
                aiServiceUrl + "/query/stream",
                new AiQueryRequest(aiQuestion, AI_TOP_K, history),
                (accumulatedAnswer, capturedEvents) -> {
                    ChatMessage assistantMsg = new ChatMessage();
                    assistantMsg.setSessionId(sessionId);
                    assistantMsg.setRole(MessageRole.ASSISTANT);
                    assistantMsg.setContent(accumulatedAnswer);
                    assistantMsg.setSequence(nextSequence + 1);
                    messageRepository.save(assistantMsg);

                    session.setUpdatedAt(LocalDateTime.now().toString());
                    sessionRepository.save(session);
                },
                (err, emitter) -> {
                    log.error("Chat stream failed for session {}: {}", sessionId, err.getMessage());
                    emitter.completeWithError(err);
                });
    }

    /**
     * Last {@value #HISTORY_MAX_MESSAGES} TEXT messages of the session (oldest
     * first), contents truncated to {@value #HISTORY_CONTENT_MAX_CHARS} chars,
     * for conversation-aware retrieval in the AI service. TIMELINE messages
     * are excluded.
     */
    private List<AiQueryRequest.ConversationTurn> buildConversationHistory(String sessionId) {
        List<ChatMessage> messages = messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
        List<AiQueryRequest.ConversationTurn> turns = new ArrayList<>();
        for (int i = messages.size() - 1; i >= 0 && turns.size() < HISTORY_MAX_MESSAGES; i--) {
            ChatMessage msg = messages.get(i);
            if (msg.getMessageType() == MessageType.TIMELINE
                    || msg.getContent() == null || msg.getContent().isBlank()) {
                continue;
            }
            String content = msg.getContent();
            if (content.length() > HISTORY_CONTENT_MAX_CHARS) {
                content = content.substring(0, HISTORY_CONTENT_MAX_CHARS);
            }
            String role = msg.getRole() == MessageRole.ASSISTANT ? "assistant" : "user";
            turns.add(0, new AiQueryRequest.ConversationTurn(role, content));
        }
        return turns;
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

    public SseEmitter askTimelineStream(String userId, String sessionId, TimelineRequest request) {
        ChatSession session = findSessionForUser(userId, sessionId);

        long nextSequence = messageRepository.nextSequence(sessionId);

        ChatMessage userMsg = new ChatMessage();
        userMsg.setSessionId(sessionId);
        userMsg.setRole(MessageRole.USER);
        userMsg.setContent(request.question());
        userMsg.setSequence(nextSequence);
        userMsg.setMessageType(MessageType.TEXT);
        messageRepository.save(userMsg);

        session.setUpdatedAt(LocalDateTime.now().toString());
        sessionRepository.save(session);

        TimelineHistoryContext historyContext = buildTimelineHistoryContext(sessionId);

        String aiQuestion = (request.context() != null && !request.context().isBlank())
                ? "[" + request.context() + "] " + request.question()
                : request.question();

        return sseRelay.relay(
                aiServiceUrl + "/query/timeline/stream",
                new TimelineAiRequest(aiQuestion, request.context(), historyContext.currentSnapshot(), historyContext.recentExchanges()),
                (accumulatedAnswer, capturedEvents) -> {
                    String timelineRaw = capturedEvents.get("timeline");
                    String content = accumulatedAnswer;
                    String timelineJson = null;

                    if (timelineRaw != null) {
                        try {
                            TimelineSnapshotDto snapshot = objectMapper.readValue(timelineRaw, TimelineSnapshotDto.class);
                            timelineJson = objectMapper.writeValueAsString(snapshot);
                        } catch (JsonProcessingException e) {
                            log.warn("Failed to parse/serialize streamed timeline snapshot: {}", e.getMessage());
                        }
                    }

                    ChatMessage assistantMsg = new ChatMessage();
                    assistantMsg.setSessionId(sessionId);
                    assistantMsg.setRole(MessageRole.ASSISTANT);
                    assistantMsg.setContent(content);
                    assistantMsg.setMessageType(MessageType.TIMELINE);
                    assistantMsg.setTimeline(timelineJson);
                    assistantMsg.setSequence(nextSequence + 1);
                    messageRepository.save(assistantMsg);

                    session.setUpdatedAt(LocalDateTime.now().toString());
                    sessionRepository.save(session);
                },
                (err, emitter) -> {
                    log.error("Timeline stream failed for session {}: {}", sessionId, err.getMessage());
                    emitter.completeWithError(err);
                });
    }

    private record TimelineHistoryContext(TimelineSnapshotDto currentSnapshot, List<RecentExchange> recentExchanges) {
    }

    private TimelineHistoryContext buildTimelineHistoryContext(String sessionId) {
        List<ChatMessage> recentMessages = messageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
        TimelineSnapshotDto currentSnapshot = null;
        List<RecentExchange> recentExchanges = new ArrayList<>();

        int exchangeCount = 0;
        for (int i = recentMessages.size() - 1; i >= 0 && exchangeCount < 3; i--) {
            ChatMessage msg = recentMessages.get(i);
            if (msg.getRole() == MessageRole.ASSISTANT && msg.getMessageType() == MessageType.TIMELINE) {
                if (currentSnapshot == null && msg.getTimeline() != null) {
                    try {
                        currentSnapshot = objectMapper.readValue(msg.getTimeline(), TimelineSnapshotDto.class);
                    } catch (JsonProcessingException e) {
                        log.warn("Failed to parse existing timeline snapshot: {}", e.getMessage());
                    }
                }
            }
        }

        for (int i = recentMessages.size() - 1; i >= 0 && exchangeCount < 3; i -= 2) {
            ChatMessage assistant = i >= 0 ? recentMessages.get(i) : null;
            ChatMessage user = i - 1 >= 0 ? recentMessages.get(i - 1) : null;

            if (assistant != null && assistant.getRole() == MessageRole.ASSISTANT
                    && user != null && user.getRole() == MessageRole.USER) {
                recentExchanges.add(0, new RecentExchange(user.getContent(), assistant.getContent()));
                exchangeCount++;
            } else if (assistant != null && assistant.getRole() == MessageRole.ASSISTANT) {
                recentExchanges.add(0, new RecentExchange("", assistant.getContent()));
                exchangeCount++;
            }
        }

        return new TimelineHistoryContext(currentSnapshot, recentExchanges);
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
        return new SessionDto(s.getId(), s.getUserId(), s.getTitle(),
                s.getSessionType(), s.getCreatedAt(), s.getUpdatedAt());
    }

    private MessageDto toMessageDto(ChatMessage m) {
        TimelineSnapshotDto timelineDto = null;
        if (m.getTimeline() != null) {
            try {
                timelineDto = objectMapper.readValue(m.getTimeline(), TimelineSnapshotDto.class);
            } catch (JsonProcessingException e) {
                log.warn("Failed to deserialize timeline for message {}: {}", m.getId(), e.getMessage());
            }
        }
        return new MessageDto(m.getId(), m.getSessionId(), m.getRole(), m.getContent(),
                m.getMessageType(), timelineDto, m.getCreatedAt(), m.getSequence());
    }
}
