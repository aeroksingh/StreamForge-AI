package com.streamforge.backend.service;


import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Service
@RequiredArgsConstructor
@Slf4j
public class RedisQueueService {

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    // Python service
    private static final String DOWNLOAD_QUEUE = "download_queue";
    private static final String PROGRESS_KEY_PREFIX = "progress:";

    /**
     * Python service 
     */
    public void pushDownloadJob(UUID jobId, String youtubeUrl, String quality, String format) {
        try {
            Map<String, String> jobData = new HashMap<>();
            jobData.put("job_id", jobId.toString());
            jobData.put("youtube_url", youtubeUrl);
            jobData.put("quality", quality);
            jobData.put("format", format);

            String json = objectMapper.writeValueAsString(jobData);
            redisTemplate.opsForList().rightPush(DOWNLOAD_QUEUE, json);

            log.info("Job queued in Redis: jobId={}, url={}", jobId, youtubeUrl);
        } catch (Exception e) {
            log.error("Redis queue push failed for jobId={}: {}", jobId, e.getMessage());
            throw new RuntimeException("Queue mein push nahi ho saka", e);
        }
    }

    /**
     * Progress fetch 
     */
    public Map<String, Object> getProgress(UUID jobId) {
        try {
            String key = PROGRESS_KEY_PREFIX + jobId;
            String value = redisTemplate.opsForValue().get(key);

            if (value != null) {
                return objectMapper.readValue(value, Map.class);
            }
        } catch (Exception e) {
            log.warn("Progress fetch failed for jobId={}: {}", jobId, e.getMessage());
        }
        return new HashMap<>();
    }

    /**
     * Queue size
     */
    public long getQueueSize() {
        Long size = redisTemplate.opsForList().size(DOWNLOAD_QUEUE);
        return size != null ? size : 0;
    }
}