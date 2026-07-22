package com.vietnamhistory.userservice.dto;

import jakarta.validation.constraints.NotBlank;

public record UpdateUserRequest(
        @NotBlank(message = "Username is required")
        String username,
        String role,          // optional, admin only
        String status,        // optional, admin only: "ACTIVE" or "INACTIVE"
        String statusReason   // required when status = "INACTIVE"
) {}
