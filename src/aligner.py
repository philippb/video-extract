from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptSlideAligner:
    def __init__(self):
        pass
    
    def align_transcript_with_slides(
        self, 
        transcript: List[Dict[str, Any]], 
        slides: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not transcript or not slides:
            logger.warning("Empty transcript or slides provided for alignment")
            return []
        
        slides_sorted = sorted(slides, key=lambda x: x['timestamp'])
        aligned_slides = []
        
        for i, slide in enumerate(slides_sorted):
            start_time = slide['timestamp']
            
            if i + 1 < len(slides_sorted):
                end_time = slides_sorted[i + 1]['timestamp']
            else:
                end_time = float('inf')
            
            transcript_chunk = self._get_transcript_chunk(transcript, start_time, end_time)
            
            aligned_slide = {
                'slide_number': i + 1,
                'timestamp': start_time,
                'image_path': slide['image_path'],
                'video_id': slide.get('video_id'),
                'transcript_chunk': transcript_chunk,
                'transcript_text': self._format_transcript_text(transcript_chunk),
                'duration': self._calculate_chunk_duration(transcript_chunk),
                'word_count': self._count_words(transcript_chunk)
            }
            
            if 'image_hash' in slide:
                aligned_slide['image_hash'] = slide['image_hash']
            
            aligned_slides.append(aligned_slide)
        
        logger.info(f"Aligned {len(aligned_slides)} slides with transcript")
        return aligned_slides
    
    def _get_transcript_chunk(
        self, 
        transcript: List[Dict[str, Any]], 
        start_time: float, 
        end_time: float
    ) -> List[Dict[str, Any]]:
        chunk = []
        
        for entry in transcript:
            entry_start = entry.get('start', 0.0)
            entry_end = entry.get('end', entry_start)
            
            if self._overlaps_with_timerange(entry_start, entry_end, start_time, end_time):
                chunk.append(entry)
        
        return chunk
    
    def _overlaps_with_timerange(
        self, 
        entry_start: float, 
        entry_end: float, 
        range_start: float, 
        range_end: float
    ) -> bool:
        return not (entry_end <= range_start or entry_start >= range_end)
    
    def _format_transcript_text(self, transcript_chunk: List[Dict[str, Any]]) -> str:
        if not transcript_chunk:
            return ""
        
        texts = []
        for entry in transcript_chunk:
            text = entry.get('text', '').strip()
            if text:
                texts.append(text)
        
        return ' '.join(texts)
    
    def _calculate_chunk_duration(self, transcript_chunk: List[Dict[str, Any]]) -> float:
        if not transcript_chunk:
            return 0.0
        
        start_time = min(entry.get('start', 0.0) for entry in transcript_chunk)
        end_time = max(entry.get('end', entry.get('start', 0.0)) for entry in transcript_chunk)
        
        return max(0.0, end_time - start_time)
    
    def _count_words(self, transcript_chunk: List[Dict[str, Any]]) -> int:
        text = self._format_transcript_text(transcript_chunk)
        if not text:
            return 0
        
        return len(text.split())
    
    def get_slide_context(
        self, 
        aligned_slides: List[Dict[str, Any]], 
        slide_index: int, 
        context_window: int = 1
    ) -> Dict[str, Any]:
        if not aligned_slides or slide_index < 0 or slide_index >= len(aligned_slides):
            return {}
        
        current_slide = aligned_slides[slide_index]
        context = {
            'current': current_slide,
            'previous': [],
            'next': []
        }
        
        start_idx = max(0, slide_index - context_window)
        end_idx = min(len(aligned_slides), slide_index + context_window + 1)
        
        for i in range(start_idx, slide_index):
            context['previous'].append(aligned_slides[i])
        
        for i in range(slide_index + 1, end_idx):
            context['next'].append(aligned_slides[i])
        
        return context
    
    def filter_slides_by_content(
        self, 
        aligned_slides: List[Dict[str, Any]], 
        min_words: int = 5, 
        min_duration: float = 3.0
    ) -> List[Dict[str, Any]]:
        filtered_slides = []
        
        for slide in aligned_slides:
            word_count = slide.get('word_count', 0)
            duration = slide.get('duration', 0.0)
            
            if word_count >= min_words and duration >= min_duration:
                filtered_slides.append(slide)
            else:
                logger.debug(
                    f"Filtered out slide {slide.get('slide_number')} "
                    f"(words: {word_count}, duration: {duration:.1f}s)"
                )
        
        logger.info(f"Content filtering: {len(aligned_slides)} -> {len(filtered_slides)} slides")
        return filtered_slides
    
    def merge_short_segments(
        self, 
        aligned_slides: List[Dict[str, Any]], 
        min_duration: float = 10.0
    ) -> List[Dict[str, Any]]:
        if not aligned_slides:
            return []
        
        merged_slides = []
        current_slide = aligned_slides[0].copy()
        
        for i in range(1, len(aligned_slides)):
            next_slide = aligned_slides[i]
            
            if current_slide.get('duration', 0.0) < min_duration:
                current_slide = self._merge_slides(current_slide, next_slide)
            else:
                merged_slides.append(current_slide)
                current_slide = next_slide.copy()
        
        merged_slides.append(current_slide)
        
        for i, slide in enumerate(merged_slides):
            slide['slide_number'] = i + 1
        
        logger.info(f"Segment merging: {len(aligned_slides)} -> {len(merged_slides)} slides")
        return merged_slides
    
    def _merge_slides(self, slide1: Dict[str, Any], slide2: Dict[str, Any]) -> Dict[str, Any]:
        merged = slide1.copy()
        
        merged['transcript_chunk'].extend(slide2.get('transcript_chunk', []))
        merged['transcript_text'] = self._format_transcript_text(merged['transcript_chunk'])
        merged['duration'] = self._calculate_chunk_duration(merged['transcript_chunk'])
        merged['word_count'] = self._count_words(merged['transcript_chunk'])
        
        return merged
    
    def get_alignment_stats(self, aligned_slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not aligned_slides:
            return {}
        
        total_slides = len(aligned_slides)
        total_words = sum(slide.get('word_count', 0) for slide in aligned_slides)
        total_duration = sum(slide.get('duration', 0.0) for slide in aligned_slides)
        
        durations = [slide.get('duration', 0.0) for slide in aligned_slides]
        word_counts = [slide.get('word_count', 0) for slide in aligned_slides]
        
        stats = {
            'total_slides': total_slides,
            'total_words': total_words,
            'total_duration': total_duration,
            'avg_duration_per_slide': total_duration / total_slides if total_slides > 0 else 0,
            'avg_words_per_slide': total_words / total_slides if total_slides > 0 else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'min_words': min(word_counts) if word_counts else 0,
            'max_words': max(word_counts) if word_counts else 0,
        }
        
        return stats