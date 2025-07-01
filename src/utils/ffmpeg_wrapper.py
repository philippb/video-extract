import subprocess
import json
import os
import re
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FFmpegWrapper:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> None:
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg check failed: {result.stderr}")
            logger.debug("FFmpeg available and working")
        except FileNotFoundError:
            raise RuntimeError(f"FFmpeg not found at path: {self.ffmpeg_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg version check timed out")
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {result.stderr}")
            
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFprobe timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")
    
    def extract_scenes(self, video_path: str, output_dir: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
        os.makedirs(output_dir, exist_ok=True)
        
        scene_file = os.path.join(output_dir, "scenes.txt")
        
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-vsync", "vfr",
            "-f", "null",
            "-"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            scenes = []
            for line in result.stderr.split('\n'):
                if 'showinfo' in line and 'pts_time' in line:
                    match = re.search(r'pts_time:(\d+\.?\d*)', line)
                    if match:
                        timestamp = float(match.group(1))
                        scenes.append({
                            'timestamp': timestamp,
                            'frame_info': line.strip()
                        })
            
            logger.info(f"Detected {len(scenes)} scene changes")
            return scenes
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Scene detection timed out")
    
    def extract_frames_at_times(self, video_path: str, timestamps: List[float], output_dir: str) -> List[Dict[str, Any]]:
        os.makedirs(output_dir, exist_ok=True)
        
        extracted_frames = []
        
        for i, timestamp in enumerate(timestamps):
            output_path = os.path.join(output_dir, f"slide_{i:04d}_{timestamp:.2f}s.png")
            
            cmd = [
                self.ffmpeg_path,
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                output_path
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and os.path.exists(output_path):
                    extracted_frames.append({
                        'timestamp': timestamp,
                        'image_path': output_path,
                        'frame_number': i
                    })
                    logger.debug(f"Extracted frame at {timestamp:.2f}s")
                else:
                    logger.warning(f"Failed to extract frame at {timestamp:.2f}s: {result.stderr}")
            
            except subprocess.TimeoutExpired:
                logger.warning(f"Frame extraction timed out at {timestamp:.2f}s")
                continue
        
        logger.info(f"Successfully extracted {len(extracted_frames)} frames")
        return extracted_frames
    
    def get_video_duration(self, video_path: str) -> float:
        info = self.get_video_info(video_path)
        
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                duration = stream.get('duration')
                if duration:
                    return float(duration)
        
        format_duration = info.get('format', {}).get('duration')
        if format_duration:
            return float(format_duration)
        
        raise RuntimeError("Could not determine video duration")
    
    def extract_uniform_frames(self, video_path: str, output_dir: str, interval: float = 30.0) -> List[Dict[str, Any]]:
        duration = self.get_video_duration(video_path)
        timestamps = []
        
        current_time = 0.0
        while current_time < duration:
            timestamps.append(current_time)
            current_time += interval
        
        logger.info(f"Extracting frames at {interval}s intervals for {duration:.1f}s video")
        return self.extract_frames_at_times(video_path, timestamps, output_dir)