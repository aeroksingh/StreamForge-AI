package com.streamforge.backend.service;

import com.streamforge.backend.entity.DownloadJob;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class WebSocketProgressService {

    private final SimpMessagingTemplate messagingTemplate;

    public void sendProgress(DownloadJob job) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("jobId", job.getId().toString());
            payload.put("status", job.getStatus().name());
            payload.put("progress", job.getProgressPercent());
            payload.put("title", job.getVideoTitle());
            payload.put("fileSizeBytes", job.getFileSizeBytes());

            if (job.getStatus() == DownloadJob.JobStatus.FAILED) {
                payload.put("error", job.getErrorMessage());
            }

            String destination = "/topic/progress/" + job.getId();
            messagingTemplate.convertAndSend(destination, payload);

            log.debug("WS progress sent: jobId={}, status={}", job.getId(), job.getStatus());
        } catch (Exception e) {
            log.warn("WebSocket send failed for jobId={}: {}", job.getId(), e.getMessage());
        }
    }
}