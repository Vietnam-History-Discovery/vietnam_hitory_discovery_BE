package com.vietnamhistory.userservice.controller;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.vietnamhistory.userservice.dto.UpdateUserRequest;
import com.vietnamhistory.userservice.dto.UserDto;
import com.vietnamhistory.userservice.entity.User;
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
    public ResponseEntity<List<UserDto>> listUsers(
            @RequestHeader(value = "X-User-Role", required = false) String role) {
        requireAdmin(role);
        return ResponseEntity.ok(userRepository.findAll().stream().map(this::toDto).toList());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(
            @PathVariable String id,
            @RequestHeader(value = "X-User-Role", required = false) String role,
            @RequestHeader("X-User-Id") String callerUserId) {
        requireAdmin(role);
        if (id.equals(callerUserId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Cannot delete your own account");
        }
        userRepository.deleteById(id);
        try {
            FirebaseAuth.getInstance().deleteUser(id);
        } catch (FirebaseAuthException e) {
        }
        return ResponseEntity.noContent().build();
    }

    private void requireAdmin(String role) {
        if (!"admin".equals(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Admin role required");
        }
    }

    private UserDto toDto(User user) {
        return new UserDto(user.getId(), user.getUsername(), user.getEmail(), user.getRole().name());
    }
}
