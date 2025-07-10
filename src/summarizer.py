import base64
import time
from typing import List, Dict, Any
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openai import RateLimitError, APITimeoutError
from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlideSummarizer:
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.OPENAI_MAX_TOKENS
        self.last_request_time = 0
        self.request_count = 0
        self.minute_start = time.time()

    def _wait_for_rate_limit(self, estimated_tokens: int = 1000):
        """Wait to respect rate limits based on OpenAI tier"""
        current_time = time.time()

        # Reset counter if a minute has passed
        if current_time - self.minute_start >= 60:
            logger.debug(
                f"Resetting rate limit counter (was {self.request_count} requests)"
            )
            self.request_count = 0
            self.minute_start = current_time

        # Get rate limits for current tier
        limits = self.config.get_rate_limits()
        delay = self.config.get_delay_between_requests()

        logger.debug(
            f"Rate limit check: {self.request_count}/{limits['requests']} requests, "
            f"tokens: ~{estimated_tokens}, tier: {self.config.OPENAI_TIER}"
        )

        # Check if we're approaching rate limits
        if self.request_count >= limits["requests"] * 0.8:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                logger.warning(
                    f"Approaching rate limit "
                    f"({self.request_count}/{limits['requests']}), "
                    f"waiting {wait_time:.1f}s to reset counter"
                )
                time.sleep(wait_time)
                self.request_count = 0
                self.minute_start = time.time()

        # Ensure minimum delay between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < delay:
            wait_time = delay - time_since_last
            logger.debug(
                f"Rate limiting: waiting {wait_time:.2f}s between requests "
                f"(need {delay:.2f}s)"
            )
            time.sleep(wait_time)

        self.last_request_time = time.time()
        self.request_count += 1

        logger.debug(
            f"Making request {self.request_count}/{limits['requests']} "
            f"(Tier {self.config.OPENAI_TIER})"
        )

    def summarize_slides(
        self, aligned_slides: List[Dict[str, Any]], use_vision: bool = True
    ) -> List[Dict[str, Any]]:
        summarized_slides = []

        logger.info(f"Starting summarization of {len(aligned_slides)} slides")
        logger.info(
            f"OpenAI settings: model={self.model}, tier={self.config.OPENAI_TIER}"
        )

        limits = self.config.get_rate_limits()
        delay = self.config.get_delay_between_requests()
        logger.info(
            f"Rate limits: {limits['requests']} req/min, {limits['tokens']} tokens/min"
        )
        logger.info(f"Configured delay between requests: {delay:.2f}s")

        for slide in aligned_slides:
            try:
                logger.info(
                    f"Summarizing slide {slide.get('slide_number', 'unknown')}"
                )

                # Estimate tokens and wait for rate limit
                transcript_text = slide.get("transcript_text", "")
                ocr_text = slide.get("ocr_text", "")
                text_to_analyze = transcript_text + " " + ocr_text
                estimated_tokens = self.config.estimate_tokens(text_to_analyze)

                logger.debug(
                    f"Estimated tokens for slide {slide.get('slide_number')}: {estimated_tokens}"
                )
                self._wait_for_rate_limit(estimated_tokens)

                if use_vision and self._supports_vision():
                    logger.debug(
                        f"Using vision model for slide {slide.get('slide_number')}"
                    )
                    summary = self._summarize_with_vision(slide)
                else:
                    logger.debug(
                        f"Using text-only model for slide {slide.get('slide_number')}"
                    )
                    summary = self._summarize_with_text_only(slide)

                slide_copy = slide.copy()
                slide_copy.update(summary)
                summarized_slides.append(slide_copy)
                logger.info(
                    f"Successfully summarized slide {slide.get('slide_number')}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to summarize slide {slide.get('slide_number')}: {type(e).__name__}: {e}"
                )

                # If it's a rate limit error, show more details
                if "RateLimitError" in str(type(e)):
                    logger.error(
                        f"Rate limit hit despite proactive limiting. Tier: {self.config.OPENAI_TIER}"
                    )
                    logger.error(f"Requests this minute: {self.request_count}")
                    logger.error(
                        f"Time since minute start: {time.time() - self.minute_start:.1f}s"
                    )

                # Log the full exception for debugging
                import traceback

                logger.debug(f"Full traceback: {traceback.format_exc()}")

                slide_copy = slide.copy()
                slide_copy.update(
                    {
                        "summary": f"[Error: Could not generate summary - {str(e)}]",
                        "title": f"Slide {slide.get('slide_number', 'Unknown')}",
                        "key_points": [],
                        "topics": [],
                    }
                )
                summarized_slides.append(slide_copy)

        logger.info(
            f"Completed summarization for {len(summarized_slides)} slides"
        )
        return summarized_slides

    def _supports_vision(self) -> bool:
        return "vision" in self.model.lower() or "gpt-4" in self.model.lower()

    @retry(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    )
    def _summarize_with_vision(self, slide: Dict[str, Any]) -> Dict[str, Any]:
        image_path = slide["image_path"]
        transcript_text = slide.get("transcript_text", "")
        ocr_text = slide.get("ocr_text", "")

        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        prompt = self._create_vision_prompt(transcript_text, ocr_text)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ]

        logger.debug(
            f"Making OpenAI API call with model: {self.model}, max_tokens: {self.max_tokens}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7,
            )

            logger.debug(
                f"API call successful, tokens used: {getattr(response.usage, 'total_tokens', 'unknown')}"
            )
            return self._parse_response(response.choices[0].message.content)

        except Exception as api_error:
            logger.error(
                f"OpenAI API error: {type(api_error).__name__}: {api_error}"
            )
            raise

    @retry(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    )
    def _summarize_with_text_only(
        self, slide: Dict[str, Any]
    ) -> Dict[str, Any]:
        transcript_text = slide.get("transcript_text", "")
        ocr_text = slide.get("ocr_text", "")
        combined_text = slide.get("combined_text", "")

        if combined_text:
            content = combined_text
        else:
            content_parts = []
            if transcript_text:
                content_parts.append(f"Transcript: {transcript_text}")
            if ocr_text:
                content_parts.append(f"Slide text: {ocr_text}")
            content = "\n\n".join(content_parts)

        prompt = self._create_text_only_prompt(content)

        messages = [{"role": "user", "content": prompt}]

        logger.debug(
            f"Making OpenAI API call with model: {self.model}, max_tokens: {self.max_tokens}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7,
            )

            logger.debug(
                f"API call successful, tokens used: {getattr(response.usage, 'total_tokens', 'unknown')}"
            )
            return self._parse_response(response.choices[0].message.content)

        except Exception as api_error:
            logger.error(
                f"OpenAI API error: {type(api_error).__name__}: {api_error}"
            )
            raise

    def _create_vision_prompt(
        self, transcript_text: str, ocr_text: str
    ) -> str:
        prompt = """Analyze this slide image and the associated content to create a comprehensive summary.

SLIDE CONTENT:
"""

        if transcript_text:
            prompt += f"\nTranscript (what was said): {transcript_text}"

        if ocr_text:
            prompt += f"\nText detected on slide: {ocr_text}"

        prompt += """

Please provide a structured analysis in the following format:

TITLE: [A clear, descriptive title for this slide]

SUMMARY: [A concise 2-3 sentence summary of the main content and message]

KEY POINTS:
- [Main point 1]
- [Main point 2]
- [Main point 3, if applicable]

TOPICS: [List of 2-4 main topics/themes covered, separated by commas]

Focus on the most important information and ensure the summary is useful for someone who hasn't seen the original content."""

        return prompt

    def _create_text_only_prompt(self, content: str) -> str:
        prompt = """Analyze the following slide content and create a comprehensive summary:

CONTENT:
{content}

Please provide a structured analysis in the following format:

TITLE: [A clear, descriptive title for this slide]

SUMMARY: [A concise 2-3 sentence summary of the main content and message]

KEY POINTS:
- [Main point 1]
- [Main point 2]
- [Main point 3, if applicable]

TOPICS: [List of 2-4 main topics/themes covered, separated by commas]

Focus on the most important information and ensure the summary is useful for someone who hasn't seen the original content."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        result = {"title": "", "summary": "", "key_points": [], "topics": []}

        if not response_text:
            return result

        lines = response_text.strip().split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("TITLE:"):
                result["title"] = line.replace("TITLE:", "").strip()
                current_section = "title"
            elif line.startswith("SUMMARY:"):
                result["summary"] = line.replace("SUMMARY:", "").strip()
                current_section = "summary"
            elif line.startswith("KEY POINTS:"):
                current_section = "key_points"
            elif line.startswith("TOPICS:"):
                topics_text = line.replace("TOPICS:", "").strip()
                result["topics"] = [
                    topic.strip()
                    for topic in topics_text.split(",")
                    if topic.strip()
                ]
                current_section = "topics"
            elif (
                current_section == "summary"
                and line
                and not line.startswith("-")
            ):
                if result["summary"]:
                    result["summary"] += " " + line
                else:
                    result["summary"] = line
            elif current_section == "key_points" and line.startswith("-"):
                point = line.replace("-", "").strip()
                if point:
                    result["key_points"].append(point)

        if not result["title"]:
            result["title"] = "Slide Summary"

        if not result["summary"]:
            result["summary"] = "No summary available."

        return result

    def create_batch_summary(
        self, summarized_slides: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total_slides = len(summarized_slides)

        all_topics = []
        all_key_points = []

        for slide in summarized_slides:
            all_topics.extend(slide.get("topics", []))
            all_key_points.extend(slide.get("key_points", []))

        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        top_topics = sorted(
            topic_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        batch_summary = {
            "total_slides": total_slides,
            "main_topics": [topic for topic, count in top_topics],
            "total_key_points": len(all_key_points),
            "slides_with_content": len(
                [
                    s
                    for s in summarized_slides
                    if s.get("summary")
                    and s["summary"] != "No summary available."
                ]
            ),
        }

        return batch_summary

    def dry_run(
        self, aligned_slides: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        logger.info("Running in dry-run mode - no API calls will be made")

        dry_run_slides = []
        for slide in aligned_slides:
            slide_copy = slide.copy()
            slide_copy.update(
                {
                    "title": f"[DRY RUN] Slide {slide.get('slide_number', 'Unknown')}",
                    "summary": f"[DRY RUN] This would be a summary of slide {slide.get('slide_number')} with {slide.get('word_count', 0)} words from transcript.",
                    "key_points": [
                        "[DRY RUN] Key point 1",
                        "[DRY RUN] Key point 2",
                        "[DRY RUN] Key point 3",
                    ],
                    "topics": ["topic1", "topic2", "topic3"],
                }
            )
            dry_run_slides.append(slide_copy)

        return dry_run_slides
