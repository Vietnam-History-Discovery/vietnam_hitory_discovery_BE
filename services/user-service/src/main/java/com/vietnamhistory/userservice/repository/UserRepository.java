package com.vietnamhistory.userservice.repository;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.firebase.cloud.FirestoreClient;
import com.vietnamhistory.userservice.entity.User;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.concurrent.ExecutionException;

@Repository
public class UserRepository {

    private Firestore getFirestore() {
        return FirestoreClient.getFirestore();
    }

    public Optional<User> findById(String id) {
        try {
            var doc = getFirestore().collection("users").document(id).get().get();
            if (doc.exists()) {
                return Optional.ofNullable(doc.toObject(User.class));
            }
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
        return Optional.empty();
    }

    public boolean existsByUsername(String username) {
        try {
            var query = getFirestore().collection("users").whereEqualTo("username", username).get().get();
            return !query.isEmpty();
        } catch (InterruptedException | ExecutionException e) {
            Thread.currentThread().interrupt();
        }
        return false;
    }

    public User save(User user) {
        getFirestore().collection("users").document(user.getId()).set(user);
        return user;
    }
}
