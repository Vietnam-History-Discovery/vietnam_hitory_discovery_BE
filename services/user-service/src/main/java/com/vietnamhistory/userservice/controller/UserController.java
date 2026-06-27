package com.vietnamhistory.userservice.controller;

import com.vietnamhistory.userservice.dto.UpdateUserRequest;
import com.vietnamhistory.userservice.dto.UserDto;
import com.vietnamhistory.userservice.entity.User;
import com.vietnamhistory.userservice.repository.UserRepository;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

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

    private UserDto toDto(User user) {
        return new UserDto(user.getId(), user.getUsername(), user.getEmail(), user.getRole().name());
    }
}
