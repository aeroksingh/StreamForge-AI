package com.streamforge.backend.service;

import com.streamforge.backend.dto.DownloadRequestDto;
import com.streamforge.backend.dto.JobResponseDto;
import com.streamforge.backend.entity.DownloadJob;
import com.streamforge.backend.repository.DownloadJobRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class DownloadService {

    private final DownloadJobRepository jobRepository;
    private final RedisQueueService redisQueueService;
    private final WebSocketProgressService wsProgressService;

    @Value("${app.python.service.url}")
    private String pythonServiceUrl;

    @Transactional
    public JobResponseDto createJob(DownloadRequestDto request,
                                    HttpServletRequest httpRequest,
                                    String baseUrl) {
        String clientIp = getClientIp(httpRequest);

        DownloadJob job = DownloadJob.builder()
                .youtubeUrl(request.getYoutubeUrl())
                .videoTitle("Fetching...")
                .quality(request.getQuality() != null ? request.getQuality() : "unknown")
                .format(request.getFormat() != null ? request.getFormat() : "mp4")
                .status(DownloadJob.JobStatus.PENDING)
                .progressPercent(0)
                .requestedBy(clientIp)
                .build();

        job = jobRepository.save(job);
        log.info("Job created: id={}, url={}", job.getId(), job.getYoutubeUrl());

        try {
            // Push to Redis with videoItag + audioItag
            redisQueueService.pushDownloadJob(
                    job.getId(),
                    job.getYoutubeUrl(),
                    request.getVideoItag(),
                    request.getAudioItag(),
                    job.getQuality(),
                    job.getFormat()
            );
            job.setStatus(DownloadJob.JobStatus.QUEUED);
            job = jobRepository.save(job);
        } catch (Exception e) {
            log.error("Queue push failed: {}", e.getMessage());
            job.setStatus(DownloadJob.JobStatus.FAILED);
            job.setErrorMessage("Queue error: " + e.getMessage());
            job = jobRepository.save(job);
        }

        return JobResponseDto.from(job, baseUrl);
    }

    public JobResponseDto getJobStatus(UUID jobId, String baseUrl) {
        DownloadJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job nahi mila: " + jobId));
        return JobResponseDto.from(job, baseUrl);
    }

    public List<JobResponseDto> getUserJobs(String requestedBy, String baseUrl) {
        return jobRepository.findByRequestedByOrderByCreatedAtDesc(requestedBy)
                .stream()
                .map(job -> JobResponseDto.from(job, baseUrl))
                .collect(Collectors.toList());
    }

    /**
     * Har 2 seconds mein Redis se Python ka progress read karo
     * aur DB + WebSocket update karo
     */
    @Scheduled(fixedDelay = 2000)
    @Transactional
    public void syncProgressFromRedis() {
        List<DownloadJob> activeJobs = jobRepository.findActiveJobs();

        for (DownloadJob job : activeJobs) {
            try {
                Map<String, Object> progress = redisQueueService.getProgress(job.getId());
                if (progress.isEmpty()) continue;

                boolean changed = false;

                if (progress.containsKey("status")) {
                    String s = (String) progress.get("status");
                    try {
                        // Map Python status → Java enum
                        DownloadJob.JobStatus newStatus = mapStatus(s);
                        if (newStatus != job.getStatus()) {
                            job.setStatus(newStatus);
                            changed = true;
                        }
                    } catch (IllegalArgumentException ignored) {}
                }

                if (progress.containsKey("progress")) {
                    int pct = ((Number) progress.get("progress")).intValue();
                    if (!Integer.valueOf(pct).equals(job.getProgressPercent())) {
                        job.setProgressPercent(pct);
                        changed = true;
                    }
                }

                if (progress.containsKey("title")) {
                    String title = (String) progress.get("title");
                    if (title != null && !title.equals("Fetching...")) {
                        job.setVideoTitle(title);
                        changed = true;
                    }
                }

                if (progress.containsKey("file_path")) {
                    job.setFilePath((String) progress.get("file_path"));
                    changed = true;
                }

                if (progress.containsKey("file_size")) {
                    job.setFileSizeBytes(((Number) progress.get("file_size")).longValue());
                    changed = true;
                }

                if (progress.containsKey("error")) {
                    job.setErrorMessage((String) progress.get("error"));
                    changed = true;
                }

                if (job.getStatus() == DownloadJob.JobStatus.COMPLETED
                        && job.getCompletedAt() == null) {
                    job.setCompletedAt(LocalDateTime.now());
                    changed = true;
                }

                if (changed) {
                    jobRepository.save(job);
                    wsProgressService.sendProgress(job);
                    log.debug("Job synced: id={}, status={}, {}%",
                            job.getId(), job.getStatus(), job.getProgressPercent());
                }

            } catch (Exception e) {
                log.warn("Sync failed for jobId={}: {}", job.getId(), e.getMessage());
            }
        }
    }

    // Map Python status strings → Java enum
    private DownloadJob.JobStatus mapStatus(String s) {
        return switch (s.toLowerCase()) {
            case "queued"      -> DownloadJob.JobStatus.QUEUED;
            case "downloading" -> DownloadJob.JobStatus.DOWNLOADING;
            case "merging"     -> DownloadJob.JobStatus.MERGING;
            case "done",
                 "completed"   -> DownloadJob.JobStatus.COMPLETED;
            case "failed",
                 "error"       -> DownloadJob.JobStatus.FAILED;
            default            -> DownloadJob.JobStatus.QUEUED;
        };
    }

    private String getClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) return xff.split(",")[0].trim();
        return request.getRemoteAddr();
    }
}