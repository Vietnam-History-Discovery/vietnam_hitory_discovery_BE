package com.vietnamhistory.chatservice.dto;

import java.util.List;

public record SessionWithMessagesDto(SessionDto session, List<MessageDto> messages) {}
