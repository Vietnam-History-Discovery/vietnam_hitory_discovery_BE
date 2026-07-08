package com.vietnamhistory.userservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.userservice.entity.User;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;

@Repository
public class UserRepository {

    private static final java.util.Map<String, User> inMemoryUsers = new ConcurrentHashMap<>();

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public Optional<User> findById(String id) {
        try {
            var doc = getFirestore().collection("users").document(id).get().get();
            if (doc.exists()) {
                return Optional.ofNullable(doc.toObject(User.class));
            }
        } catch (Exception e) {
            // fallback
        }
        return Optional.ofNullable(inMemoryUsers.get(id));
    }

    public boolean existsByUsername(String username) {
        try {
            var query = getFirestore().collection("users").whereEqualTo("username", username).get().get();
            if (!query.isEmpty()) {
                return true;
            }
        } catch (Exception e) {
            // fallback
        }
        return inMemoryUsers.values().stream().anyMatch(u -> username.equals(u.getUsername()));
    }

    public User save(User user) {
        try {
            getFirestore().collection("users").document(user.getId()).set(user);
        } catch (Exception e) {
            // fallback
        }
        inMemoryUsers.put(user.getId(), user);
        return user;
    }
}
