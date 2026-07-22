package com.vietnamhistory.userservice.controller;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.vietnamhistory.userservice.dto.UpdateUserRequest;
import com.vietnamhistory.userservice.dto.UserDto;
import com.vietnamhistory.userservice.entity.Role;
import com.vietnamhistory.userservice.entity.User;
import com.vietnamhistory.userservice.entity.UserStatus;
import com.vietnamhistory.userservice.repository.UserRepository;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/me")
    public ResponseEntity<UserDto> getMe(@RequestHeader("X-User-Id") String userId,
                                         @RequestHeader(value = "X-User-Email", required = false) String email) {
        User user = userRepository.findById(userId).orElseGet(() -> {
            // Auto-create user doc if missing
            User newUser = new User(userId, email != null ? email.split("@")[0] : "User", email);
            return userRepository.save(newUser);
        });
        return ResponseEntity.ok(toDto(user));
    }

    @PutMapping("/me")
    public ResponseEntity<UserDto> updateMe(@Valid @RequestBody UpdateUserRequest request,
                                            @RequestHeader("X-User-Id") String userId,
                                            @RequestHeader(value = "X-User-Email", required = false) String email) {
        User user = userRepository.findById(userId).orElseGet(() -> {
            return new User(userId, email != null ? email.split("@")[0] : "User", email);
        });

        if (!user.getUsername().equals(request.username())
                && userRepository.existsByUsername(request.username())) {
            throw new RuntimeException("Username already taken");
        }

        user.setUsername(request.username());
        return ResponseEntity.ok(toDto(userRepository.save(user)));
    }

    @GetMapping
    public ResponseEntity<List<UserDto>> listUsers(@RequestHeader("X-User-Id") String requesterId) {
        if (!isAdmin(requesterId)) {
            return ResponseEntity.status(403).build();
        }
        return ResponseEntity.ok(userRepository.findAll().stream().map(this::toDto).toList());
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserDto> updateUser(@PathVariable String id,
                                               @Valid @RequestBody UpdateUserRequest request,
                                               @RequestHeader("X-User-Id") String requesterId) {
        if (!isAdmin(requesterId)) {
            return ResponseEntity.status(403).build();
        }
        if (id.equals(requesterId) && "INACTIVE".equals(request.status())) {
            throw new RuntimeException("Admin cannot deactivate their own account");
        }
        if ("INACTIVE".equals(request.status())
                && (request.statusReason() == null || request.statusReason().isBlank())) {
            throw new RuntimeException("Status reason is required when deactivating a user");
        }

        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("User not found"));

        user.setUsername(request.username());
        if (request.role() != null) {
            user.setRole(Role.valueOf(request.role()));
        }
        if (request.status() != null) {
            user.setStatus(UserStatus.valueOf(request.status()));
            user.setStatusReason("INACTIVE".equals(request.status()) ? request.statusReason() : null);
        }

        return ResponseEntity.ok(toDto(userRepository.save(user)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable String id,
                                            @RequestHeader("X-User-Id") String requesterId) {
        if (!isAdmin(requesterId)) {
            return ResponseEntity.status(403).build();
        }
        userRepository.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    private boolean isAdmin(String requesterId) {
        return userRepository.findById(requesterId)
                .map(u -> u.getRole() == Role.ADMIN)
                .orElse(false);
    }

    private UserDto toDto(User user) {
        return new UserDto(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getRole().name(),
                user.getStatus() != null ? user.getStatus().name() : UserStatus.ACTIVE.name(),
                user.getStatusReason()
        );
    }
}
