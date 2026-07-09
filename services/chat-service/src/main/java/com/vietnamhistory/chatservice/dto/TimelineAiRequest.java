package com.vietnamhistory.chatservice.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record TimelineAiRequest(
        String question,
        String context,
        @JsonProperty("current_snapshot") TimelineSnapshotDto currentSnapshot,
        @JsonProperty("recent_exchanges") List<RecentExchange> recentExchanges
) {
    public record RecentExchange(
            String user,
            String assistant
    ) {}
}
