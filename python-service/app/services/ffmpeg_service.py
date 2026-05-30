import subprocess
import os


def merge(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Uses FFmpeg to combine a video-only file and an audio-only file
    into one final mp4.

    -c:v copy  →  don't re-encode video   (fast, no quality loss)
    -c:a copy  →  don't re-encode audio   (fast, no quality loss)
    -map 0:v:0 →  take video track from first input
    -map 1:a:0 →  take audio track from second input
    -y         →  overwrite output if it already exists
    """
    command = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-y",
        output_path,
    ]

    print(f"[ffmpeg] merging:\n  video: {video_path}\n  audio: {audio_path}\n  output: {output_path}")

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        # ffmpeg writes errors to stderr
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr}")

    # clean up the two temp files after successful merge
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(audio_path):
        os.remove(audio_path)

    print(f"[ffmpeg] done → {output_path}")
    return output_path


def zip_files(file_paths: list, zip_output_path: str) -> str:
    """
    Zips multiple mp4 files into one archive.
    Used for playlist downloads.
    """
    import zipfile

    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in file_paths:
            if os.path.exists(path):
                # store file with just its filename, not full path
                zf.write(path, arcname=os.path.basename(path))

    return zip_output_path
