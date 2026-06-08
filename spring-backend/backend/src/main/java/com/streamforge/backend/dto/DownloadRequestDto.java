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

    @NotBlank(message = "Quality specify karo")
    @Pattern(regexp = "^(2160p|1440p|1080p|720p|480p|360p|240p|best|worst)$",
             message = "Valid quality: 1080p, 720p, 480p, 360p, best")
    private String quality;

    @Pattern(regexp = "^(mp4|mp3|webm)$", message = "Format: mp4, mp3, webm")
    private String format = "mp4";
}