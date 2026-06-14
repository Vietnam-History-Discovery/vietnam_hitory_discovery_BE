package com.vietnamhistory.userservice.dto;

import com.vietnamhistory.userservice.entity.Role;

import java.time.LocalDateTime;
import java.util.UUID;

public record UserDto(
        UUID id,
        String username,
        String email,
        Role role,
        LocalDateTime createdAt
) {}
