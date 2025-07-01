import os
import yt_dlp
import tempfile
import imagehash
from PIL import Image
from typing import List, Dict, Any, Optional
from src.config import Config
from src.utils.ffmpeg_wrapper import FFmpegWrapper
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlideExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.ffmpeg = FFmpegWrapper(config.FFMPEG_PATH)
    
    def extract_slides(self, video_id: str, scene_threshold: float = None) -> List[Dict[str, Any]]:
        scene_threshold = scene_threshold or self.config.SCENE_THRESHOLD
        
        video_path = self._download_video(video_id)
        try:
            slides = self._extract_slides_from_video(video_path, video_id, scene_threshold)
            slides = self._remove_duplicates(slides)
            slides = self._filter_slides(slides)
            
            logger.info(f"Extracted {len(slides)} unique slides for video {video_id}")
            return slides
            
        finally:
            if video_path and os.path.exists(video_path):
                os.unlink(video_path)
                logger.debug(f"Cleaned up temporary video file: {video_path}")
    
    def _download_video(self, video_id: str) -> str:
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, f"{video_id}.%(ext)s")
        
        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                
                if os.path.exists(downloaded_file):
                    logger.info(f"Downloaded video: {downloaded_file}")
                    return downloaded_file
                
                possible_files = [
                    downloaded_file.replace('.webm', '.mp4'),
                    downloaded_file.replace('.mp4', '.webm'),
                ]
                
                for file_path in possible_files:
                    if os.path.exists(file_path):
                        logger.info(f"Found downloaded video: {file_path}")
                        return file_path
                
                raise RuntimeError(f"Could not find downloaded video file for {video_id}")
                
        except Exception as e:
            logger.error(f"Error downloading video {video_id}: {e}")
            raise
    
    def _extract_slides_from_video(self, video_path: str, video_id: str, scene_threshold: float) -> List[Dict[str, Any]]:
        output_dir = self.config.get_slides_dir(video_id)
        
        try:
            scenes = self.ffmpeg.extract_scenes(video_path, output_dir, scene_threshold)
            
            if not scenes:
                logger.warning(f"No scene changes detected, using uniform sampling")
                return self._extract_uniform_slides(video_path, video_id)
            
            timestamps = [scene['timestamp'] for scene in scenes]
            timestamps = self._filter_timestamps(timestamps)
            
            if len(timestamps) > self.config.MAX_SLIDES:
                logger.warning(f"Too many slides detected ({len(timestamps)}), limiting to {self.config.MAX_SLIDES}")
                timestamps = timestamps[:self.config.MAX_SLIDES]
            
            frames = self.ffmpeg.extract_frames_at_times(video_path, timestamps, output_dir)
            
            slides = []
            for frame in frames:
                slides.append({
                    'timestamp': frame['timestamp'],
                    'image_path': frame['image_path'],
                    'frame_number': frame['frame_number'],
                    'video_id': video_id
                })
            
            return slides
            
        except Exception as e:
            logger.error(f"Error extracting slides with scene detection: {e}")
            return self._extract_uniform_slides(video_path, video_id)
    
    def _extract_uniform_slides(self, video_path: str, video_id: str) -> List[Dict[str, Any]]:
        output_dir = self.config.get_slides_dir(video_id)
        interval = 30.0
        
        logger.info(f"Extracting slides at {interval}s intervals")
        frames = self.ffmpeg.extract_uniform_frames(video_path, output_dir, interval)
        
        slides = []
        for frame in frames:
            slides.append({
                'timestamp': frame['timestamp'],
                'image_path': frame['image_path'],
                'frame_number': frame['frame_number'],
                'video_id': video_id
            })
        
        return slides
    
    def _filter_timestamps(self, timestamps: List[float]) -> List[float]:
        if not timestamps:
            return []
        
        filtered = [timestamps[0]]
        
        for timestamp in timestamps[1:]:
            if timestamp - filtered[-1] >= self.config.MIN_SLIDE_DURATION:
                filtered.append(timestamp)
        
        return filtered
    
    def _remove_duplicates(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not slides:
            return slides
        
        unique_slides = []
        seen_hashes = set()
        
        for slide in slides:
            try:
                image_path = slide['image_path']
                if not os.path.exists(image_path):
                    continue
                
                with Image.open(image_path) as img:
                    img_hash = imagehash.average_hash(img)
                    
                    is_duplicate = any(
                        img_hash - seen_hash < 5 for seen_hash in seen_hashes
                    )
                    
                    if not is_duplicate:
                        seen_hashes.add(img_hash)
                        slide['image_hash'] = str(img_hash)
                        unique_slides.append(slide)
                    else:
                        os.unlink(image_path)
                        logger.debug(f"Removed duplicate slide: {image_path}")
                        
            except Exception as e:
                logger.warning(f"Error processing slide {slide.get('image_path')}: {e}")
                continue
        
        logger.info(f"Removed {len(slides) - len(unique_slides)} duplicate slides")
        return unique_slides
    
    def _filter_slides(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered_slides = []
        
        for slide in slides:
            try:
                image_path = slide['image_path']
                if not os.path.exists(image_path):
                    continue
                
                with Image.open(image_path) as img:
                    if self._is_valid_slide(img):
                        filtered_slides.append(slide)
                    else:
                        os.unlink(image_path)
                        logger.debug(f"Filtered out invalid slide: {image_path}")
                        
            except Exception as e:
                logger.warning(f"Error filtering slide {slide.get('image_path')}: {e}")
                continue
        
        logger.info(f"Filtered slides: {len(slides)} -> {len(filtered_slides)}")
        return filtered_slides
    
    def _is_valid_slide(self, img: Image.Image) -> bool:
        width, height = img.size
        
        if width < 320 or height < 240:
            return False
        
        img_gray = img.convert('L')
        pixels = list(img_gray.getdata())
        
        black_pixels = sum(1 for p in pixels if p < 30)
        white_pixels = sum(1 for p in pixels if p > 225)
        total_pixels = len(pixels)
        
        if black_pixels / total_pixels > 0.9:
            return False
        
        if white_pixels / total_pixels > 0.9:
            return False
        
        return True
    
    def load_slides(self, video_id: str) -> List[Dict[str, Any]]:
        slides_dir = self.config.get_slides_dir(video_id)
        
        if not os.path.exists(slides_dir):
            return []
        
        slides = []
        for filename in sorted(os.listdir(slides_dir)):
            if filename.endswith('.png'):
                image_path = os.path.join(slides_dir, filename)
                
                try:
                    timestamp_str = filename.split('_')[1].replace('s.png', '')
                    timestamp = float(timestamp_str)
                    
                    slides.append({
                        'timestamp': timestamp,
                        'image_path': image_path,
                        'video_id': video_id
                    })
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse timestamp from filename {filename}: {e}")
                    continue
        
        return slides