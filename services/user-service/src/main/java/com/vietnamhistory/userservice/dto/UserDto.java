package com.vietnamhistory.userservice.dto;

import com.vietnamhistory.userservice.entity.Role;

import java.time.LocalDateTime;
import java.util.UUID;

public record UserDto(
        String id,
        String username,
        String email,
        String role
) {}
