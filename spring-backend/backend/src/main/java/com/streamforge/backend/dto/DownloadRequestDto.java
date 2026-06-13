package com.streamforge.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class DownloadRequestDto {

    @NotBlank(message = "YouTube URL required hai")
    @Pattern(
        regexp = "^(https?://)?(www\\.)?(youtube\\.com/watch\\?v=|youtu\\.be/)[\\w-]+.*$",
        message = "Valid YouTube URL do"
    )
    private String youtubeUrl;

    // Quality label — "1080p", "720p" etc (for DB record)
    private String quality;

    // Actual itags from extension
    private String videoItag;   // e.g. "137"
    private String audioItag;   // e.g. "140"

    @Pattern(regexp = "^(mp4|mp3|webm)$", message = "Format: mp4, mp3, webm")
    private String format = "mp4";
}