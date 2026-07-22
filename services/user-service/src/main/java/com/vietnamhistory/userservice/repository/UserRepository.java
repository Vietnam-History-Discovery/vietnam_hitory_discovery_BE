package com.vietnamhistory.userservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.userservice.entity.User;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;

@Repository
public class UserRepository {

    private static final Logger log = LoggerFactory.getLogger(UserRepository.class);

    private static final ConcurrentHashMap<String, User> inMemoryUsers = new ConcurrentHashMap<>();

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public List<User> findAll() {
        List<User> users = new ArrayList<>();
        try {
            var docs = getFirestore().collection("users").get().get();
            for (QueryDocumentSnapshot doc : docs.getDocuments()) {
                User user = doc.toObject(User.class);
                if (user != null) {
                    users.add(user);
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (ExecutionException e) {
            log.error("Failed to fetch users", e);
        }
        return users;
    }

    public void deleteById(String id) {
        try {
            getFirestore().collection("users").document(id).delete().get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (ExecutionException e) {
            log.error("Failed to delete user {}", id, e);
        }
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

    public List<User> findAll() {
        List<User> users = new ArrayList<>();
        try {
            for (QueryDocumentSnapshot doc : getFirestore().collection("users").get().get().getDocuments()) {
                users.add(doc.toObject(User.class));
            }
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
        return users;
    }

    public void deleteById(String id) {
        try {
            getFirestore().collection("users").document(id).delete().get();
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
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
