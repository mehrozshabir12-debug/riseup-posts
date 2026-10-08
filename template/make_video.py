"""Turn a post image into an 8-second 1080x1920 Reel (slow zoom, blurred background fill).
Usage: python3 make_video.py post.jpg out.mp4
"""
import subprocess, sys
src, out = sys.argv[1], sys.argv[2]
fps, dur = 30, 8
frames = fps * dur
vf = (
    "[0:v]split=2[a][b];"
    "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2,eq=brightness=-0.15[bg];"
    f"[b]scale=2160:-1,zoompan=z='min(1+0.0006*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1350:fps={fps}[fg];"
    "[bg][fg]overlay=0:(H-h)/2,format=yuv420p[v]"
)
cmd = ["ffmpeg", "-y", "-loop", "1", "-i", src, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
       "-filter_complex", vf, "-map", "[v]", "-map", "1:a", "-t", str(dur), "-r", str(fps),
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "96k",
       "-movflags", "+faststart", out]
subprocess.run(cmd, check=True, capture_output=True)
print("saved", out)
