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

    /**
     * New download job create karo
     */
    @Transactional
    public JobResponseDto createJob(DownloadRequestDto request, HttpServletRequest httpRequest, String baseUrl) {
        String clientIp = getClientIp(httpRequest);

        DownloadJob job = DownloadJob.builder()
                .youtubeUrl(request.getYoutubeUrl())
                .videoTitle("Fetching...")   // Python service baad mein update karegi
                .quality(request.getQuality())
                .format(request.getFormat())
                .status(DownloadJob.JobStatus.PENDING)
                .progressPercent(0)
                .requestedBy(clientIp)
                .build();

        job = jobRepository.save(job);
        log.info("Job created: id={}, url={}", job.getId(), job.getYoutubeUrl());

        // Redis queue mein push karo
        try {
            redisQueueService.pushDownloadJob(
                    job.getId(),
                    job.getYoutubeUrl(),
                    job.getQuality(),
                    job.getFormat()
            );
            job.setStatus(DownloadJob.JobStatus.QUEUED);
            job = jobRepository.save(job);
        } catch (Exception e) {
            log.error("Queue push failed, job marked as FAILED: {}", e.getMessage());
            job.setStatus(DownloadJob.JobStatus.FAILED);
            job.setErrorMessage("Queue mein add nahi ho saka: " + e.getMessage());
            job = jobRepository.save(job);
        }

        return JobResponseDto.from(job, baseUrl);
    }

    /**
     * Job status fetch karo
     */
    public JobResponseDto getJobStatus(UUID jobId, String baseUrl) {
        DownloadJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job nahi mila: " + jobId));
        return JobResponseDto.from(job, baseUrl);
    }

    /**
     * User ki saari jobs
     */
    public List<JobResponseDto> getUserJobs(String requestedBy, String baseUrl) {
        return jobRepository.findByRequestedByOrderByCreatedAtDesc(requestedBy)
                .stream()
                .map(job -> JobResponseDto.from(job, baseUrl))
                .collect(Collectors.toList());
    }

    /**
     * Python service se progress sync — har 2 second mein
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

                // Status update
                if (progress.containsKey("status")) {
                    String statusStr = (String) progress.get("status");
                    try {
                        DownloadJob.JobStatus newStatus = DownloadJob.JobStatus.valueOf(statusStr.toUpperCase());
                        if (newStatus != job.getStatus()) {
                            job.setStatus(newStatus);
                            changed = true;
                        }
                    } catch (IllegalArgumentException ignored) {}
                }

                // Progress percent
                if (progress.containsKey("progress")) {
                    int pct = ((Number) progress.get("progress")).intValue();
                    if (!Integer.valueOf(pct).equals(job.getProgressPercent())) {
                        job.setProgressPercent(pct);
                        changed = true;
                    }
                }

                // Title
                if (progress.containsKey("title") && !"Fetching...".equals(progress.get("title"))) {
                    job.setVideoTitle((String) progress.get("title"));
                    changed = true;
                }

                // File path (completed hone par)
                if (progress.containsKey("file_path")) {
                    job.setFilePath((String) progress.get("file_path"));
                    changed = true;
                }

                // File size
                if (progress.containsKey("file_size")) {
                    job.setFileSizeBytes(((Number) progress.get("file_size")).longValue());
                    changed = true;
                }

                // Error
                if (progress.containsKey("error")) {
                    job.setErrorMessage((String) progress.get("error"));
                    changed = true;
                }

                // Completed time
                if (job.getStatus() == DownloadJob.JobStatus.COMPLETED && job.getCompletedAt() == null) {
                    job.setCompletedAt(LocalDateTime.now());
                    changed = true;
                }

                if (changed) {
                    jobRepository.save(job);
                    // WebSocket se extension ko notify karo
                    wsProgressService.sendProgress(job);
                    log.debug("Job updated: id={}, status={}, progress={}%",
                            job.getId(), job.getStatus(), job.getProgressPercent());
                }

            } catch (Exception e) {
                log.warn("Progress sync failed for jobId={}: {}", job.getId(), e.getMessage());
            }
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}