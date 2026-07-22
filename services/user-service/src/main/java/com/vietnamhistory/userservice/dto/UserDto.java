package com.vietnamhistory.userservice.dto;

public record UserDto(
        String id,
        String username,
        String email,
        String role,
        String status,
        String statusReason
) {}
