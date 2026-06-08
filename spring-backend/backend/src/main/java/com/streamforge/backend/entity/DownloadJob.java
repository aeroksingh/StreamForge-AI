package com.streamforge.backend.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "download_jobs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DownloadJob {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 2048)
    private String youtubeUrl;

    @Column(nullable = false)
    private String videoTitle;

    @Column
    private String thumbnailUrl;

    @Column(nullable = false)
    private String quality;          // e.g. "1080p", "720p", "480p"

    @Column(nullable = false)
    private String format;           // "mp4", "mp3"

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private JobStatus status;

    @Column
    private Integer progressPercent; // 0-100

    @Column(length = 1024)
    private String filePath;         // final file ka path

    @Column(length = 512)
    private String errorMessage;

    @Column
    private Long fileSizeBytes;

    @Column(length = 100)
    private String requestedBy;      // user identifier / IP

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    @Column
    private LocalDateTime completedAt;

    public enum JobStatus {
        PENDING,
        QUEUED,
        EXTRACTING,
        DOWNLOADING,
        MERGING,
        COMPLETED,
        FAILED,
        CANCELLED
    }
}