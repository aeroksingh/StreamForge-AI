package com.streamforge.backend.repository;

import com.streamforge.backend.entity.DownloadJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface DownloadJobRepository extends JpaRepository<DownloadJob, UUID> {

    List<DownloadJob> findByRequestedByOrderByCreatedAtDesc(String requestedBy);

    List<DownloadJob> findByStatusOrderByCreatedAtDesc(DownloadJob.JobStatus status);

    @Query("SELECT j FROM DownloadJob j WHERE j.status IN ('PENDING', 'QUEUED', 'EXTRACTING', 'DOWNLOADING', 'MERGING') ORDER BY j.createdAt ASC")
    List<DownloadJob> findActiveJobs();

    long countByStatus(DownloadJob.JobStatus status);
}