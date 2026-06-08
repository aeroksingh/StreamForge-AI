package com.streamforge.backend.dto;

import com.streamforge.backend.entity.DownloadJob;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
@Builder
public class JobResponseDto {
    private UUID jobId;
    private String youtubeUrl;
    private String videoTitle;
    private String thumbnailUrl;
    private String quality;
    private String format;
    private DownloadJob.JobStatus status;
    private Integer progressPercent;
    private String downloadUrl;       // file serve karne ka URL
    private String errorMessage;
    private Long fileSizeBytes;
    private LocalDateTime createdAt;
    private LocalDateTime completedAt;

    public static JobResponseDto from(DownloadJob job, String baseUrl) {
        String downloadUrl = null;
        if (job.getStatus() == DownloadJob.JobStatus.COMPLETED && job.getFilePath() != null) {
            downloadUrl = baseUrl + "/api/download/file/" + job.getId();
        }

        return JobResponseDto.builder()
                .jobId(job.getId())
                .youtubeUrl(job.getYoutubeUrl())
                .videoTitle(job.getVideoTitle())
                .thumbnailUrl(job.getThumbnailUrl())
                .quality(job.getQuality())
                .format(job.getFormat())
                .status(job.getStatus())
                .progressPercent(job.getProgressPercent() != null ? job.getProgressPercent() : 0)
                .downloadUrl(downloadUrl)
                .errorMessage(job.getErrorMessage())
                .fileSizeBytes(job.getFileSizeBytes())
                .createdAt(job.getCreatedAt())
                .completedAt(job.getCompletedAt())
                .build();
    }
}