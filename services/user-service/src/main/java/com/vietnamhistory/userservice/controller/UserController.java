package com.vietnamhistory.userservice.controller;

import com.vietnamhistory.userservice.dto.UpdateUserRequest;
import com.vietnamhistory.userservice.dto.UserDto;
import com.vietnamhistory.userservice.entity.User;
import com.vietnamhistory.userservice.repository.UserRepository;
import com.vietnamhistory.userservice.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/me")
    public ResponseEntity<UserDto> getMe(Authentication authentication) {
        User user = findByAuth(authentication);
        return ResponseEntity.ok(AuthService.toDto(user));
    }

    @PutMapping("/me")
    public ResponseEntity<UserDto> updateMe(@Valid @RequestBody UpdateUserRequest request,
                                            Authentication authentication) {
        User user = findByAuth(authentication);

        if (!user.getUsername().equals(request.username())
                && userRepository.existsByUsername(request.username())) {
            throw new RuntimeException("Username already taken");
        }

        user.setUsername(request.username());
        return ResponseEntity.ok(AuthService.toDto(userRepository.save(user)));
    }

    private User findByAuth(Authentication authentication) {
        String email = authentication.getName();
        return userRepository.findByEmail(email)
                .orElseThrow(() -> new RuntimeException("User not found"));
    }
}
