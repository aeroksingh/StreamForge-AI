package com.streamforge.backend.controller;

import com.streamforge.backend.dto.DownloadRequestDto;
import com.streamforge.backend.dto.JobResponseDto;
import com.streamforge.backend.service.DownloadService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/download")
@RequiredArgsConstructor
@Slf4j
@CrossOrigin(origins = "*")   // Extension ke liye
public class DownloadController {

    private final DownloadService downloadService;

    @Value("${server.port:8080}")
    private String serverPort;


    @PostMapping("/start")
    public ResponseEntity<JobResponseDto> startDownload(
            @Valid @RequestBody DownloadRequestDto request,
            HttpServletRequest httpRequest) {

        String baseUrl = getBaseUrl(httpRequest);
        JobResponseDto response = downloadService.createJob(request, httpRequest, baseUrl);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }


    @GetMapping("/status/{jobId}")
    public ResponseEntity<JobResponseDto> getStatus(
            @PathVariable UUID jobId,
            HttpServletRequest httpRequest) {

        String baseUrl = getBaseUrl(httpRequest);
        return ResponseEntity.ok(downloadService.getJobStatus(jobId, baseUrl));
    }


    @GetMapping("/history")
    public ResponseEntity<List<JobResponseDto>> getHistory(HttpServletRequest httpRequest) {
        String clientIp = httpRequest.getRemoteAddr();
        String baseUrl = getBaseUrl(httpRequest);
        return ResponseEntity.ok(downloadService.getUserJobs(clientIp, baseUrl));
    }

    @GetMapping("/file/{jobId}")
    public ResponseEntity<Resource> downloadFile(@PathVariable UUID jobId, HttpServletRequest httpRequest) {
        String baseUrl = getBaseUrl(httpRequest);
        JobResponseDto job = downloadService.getJobStatus(jobId, baseUrl);

        if (job.getStatus() != com.streamforge.backend.entity.DownloadJob.JobStatus.COMPLETED) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .build();  // abhi complete nahi hua
        }

        File file = new File(job.getDownloadUrl() != null ?
                "/tmp/streamforge/downloads/" + jobId + "." + job.getFormat() :
                "");

        if (!file.exists()) {
            return ResponseEntity.notFound().build();
        }

        Resource resource = new FileSystemResource(file);
        String filename = (job.getVideoTitle() != null ?
                job.getVideoTitle().replaceAll("[^a-zA-Z0-9._-]", "_") :
                jobId.toString()) + "." + job.getFormat();

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + filename + "\"")
                .body(resource);
    }

    private String getBaseUrl(HttpServletRequest request) {
        return request.getScheme() + "://" + request.getServerName() + ":" + request.getServerPort();
    }
}