#!/usr/bin/env python3

"""
CLI: build a full bilingual review JSON from a Chinese lecture transcript.

Usage (from repo root):

    python -m apps.lecture_review.build_review path/to/transcript.txt \
        --lecture-id lecture1 \
        --output-dir outputs/lecture_reviews

The script will:
- Read the transcript.
- Call an LLM (e.g. DeepSeek) with JSON-only prompts to:
  - Segment the lecture.
  - Extract vocab/phrases per segment.
  - Generate bilingual comprehension/production questions.
  - Generate cloze items.
  - Produce lecture-level summaries and takeaways.
- Save a single JSON file combining all of the above.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a bilingual review JSON from a Chinese lecture transcript.",
    )
    parser.add_argument(
        "transcript_path",
        type=str,
        help="Path to the Chinese lecture transcript (UTF-8 text).",
    )
    parser.add_argument(
        "--lecture-id",
        type=str,
        default=None,
        help="Optional lecture identifier to embed in the output JSON. Defaults to transcript filename stem.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/lecture_reviews",
        help="Directory to write the final review JSON file. Default: outputs/lecture_reviews",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepseek-chat",
        help="Model name for the DeepSeek-compatible API.",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default="https://api.deepseek.com",
        help="Base URL for the DeepSeek-compatible API.",
    )
    return parser.parse_args()


def load_transcript(transcript_path: Path) -> str:
    return transcript_path.read_text(encoding="utf-8")


def get_api_key() -> str:
    """
    Load API key from environment or .env file.

    Priority:
    - DEEPSEEK_API_KEY
    - deepseek (for backwards compatibility with existing .env)
    """
    load_dotenv()
    key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("deepseek")
    if not key:
        raise SystemExit(
            "Missing API key. Please set DEEPSEEK_API_KEY or deepseek in your environment or .env file.",
        )
    return key


def call_llm(
    api_key: str,
    api_base: str,
    model: str,
    prompt: str,
) -> str:
    """
    Call a DeepSeek-compatible chat completion endpoint and return the raw content string.

    The prompt must already instruct the model to output strict JSON.
    """
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.1,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as error:
        raise RuntimeError(f"Unexpected LLM response structure: {data}") from error
    return content


def parse_json_from_llm(raw_content: str) -> Dict[str, Any]:
    """
    Parse JSON content returned by the LLM.
    Assumes the model followed instructions and returned JSON only.
    """
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Failed to parse JSON from LLM output: {raw_content}") from error


def build_segmentation_prompt(transcript: str) -> str:
    return f"""
You are a precise assistant for processing Chinese academic lecture transcripts.

Your task:
- Input: a full Chinese lecture transcript as plain text.
- Output: segment this transcript into short, meaningful chunks suitable for review.

Segmentation rules:
- Aim for segments of about 1–2 sentences each.
- Each segment should correspond roughly to about 5–20 seconds of speech.
- Keep sentences intact; do not split in the middle of a sentence.
- Group closely related short sentences together if they form a clear unit of meaning.
- Do NOT add or invent new content.
- Do NOT reorder any text.
- Use ONLY Chinese that actually appears in the transcript for the "chinese" field.

For each segment, you must also provide a brief English paraphrase:
- "summary_en" should be a natural English paraphrase (NOT word-for-word),
- length: 1–2 sentences,
- capture the main idea of the segment only,
- do not introduce new facts that are not in the segment.

Output format:
- Respond in VALID JSON only.
- Do NOT include any explanation, comments, or extra text outside the JSON.
- Use snake_case for all keys.
- Root object must have a single key "segments".
- "segments" is an array of segment objects.
- Each segment object must have:
  - "segment_index": integer, 0-based index in order of appearance.
  - "chinese": string, the exact Chinese text of this segment from the transcript.
  - "summary_en": string, 1–2 sentence English paraphrase of this segment.

Language constraints:
- "chinese": simplified Chinese only, no English except acronyms that appear in the transcript.
- "summary_en": natural English only, no Chinese characters.

Now segment the following lecture transcript.

TRANSCRIPT_START
{transcript}
TRANSCRIPT_END
""".strip()


def build_vocab_prompt(segment_chinese: str, segment_context: str) -> str:
    return f"""
You are a computational linguist and Mandarin teaching assistant creating advanced (HSK 6) vocabulary items from Chinese academic lecture segments.

Your task:
- Input: one Chinese segment from a lecture, optionally with brief context or topic hints.
- Output: a list of 5–12 useful vocabulary items or expressions for an advanced learner.

Selection rules:
- Focus on NON-trivial items:
  - Academic or formal vocabulary,
  - Multi-word expressions and collocations,
  - Discourse markers, stance expressions, and set phrases,
  - Topic-relevant terminology.
- Avoid very basic words (e.g. 是, 了, 有, 在) unless they are part of an important fixed expression.
- Prefer units that are pedagogically meaningful.
- Each item must either:
  - Appear explicitly in the segment, OR
  - Be a minimally adapted collocation built naturally from words in the segment.
- Example sentences:
  - "example_cn": should be taken directly from the segment where possible,
  - If necessary, you may slightly adapt or extend the sentence, but keep the meaning faithful,
  - "example_en": should be a natural English translation or close paraphrase of "example_cn".

Output format:
- Respond in VALID JSON only.
- Do NOT include any explanation, comments, or extra text outside the JSON.
- Use snake_case for all keys.
- Root object must have a single key "vocab".
- "vocab" is an array of vocabulary item objects.
- Each vocabulary item object must have:
  - "word": string, the Chinese word or expression.
  - "pinyin": string, Hanyu Pinyin with tone marks.
  - "english": string, concise English gloss or translation.
  - "example_cn": string, a natural Chinese example sentence, preferably from the segment.
  - "example_en": string, natural English translation or paraphrase of the Chinese example.

Language constraints:
- "word" and "example_cn": simplified Chinese only (with occasional English acronyms if they appear in the lecture).
- "pinyin": Pinyin with tone marks, no Chinese characters.
- "english" and "example_en": natural English only.

Input:
- "segment_chinese": the exact Chinese text of the segment.
- "segment_context": optional short description of the lecture topic in English.

Now read the following input and output the JSON.

SEGMENT_CHINESE:
{segment_chinese}

SEGMENT_CONTEXT:
{segment_context}
""".strip()


def build_questions_prompt(segment_chinese: str, segment_summary_en: str) -> str:
    return f"""
You are an expert Mandarin instructor designing advanced (HSK 6) comprehension and production questions for Chinese academic lecture segments.

Your task:
- Input: one Chinese segment and its English paraphrase.
- Output: a small set of bilingual questions that:
  - Test understanding of the segment,
  - Encourage active production in Chinese,
  - Use academic-appropriate and natural language.

Question types:
- You must include at least:
  - One "cn_comprehension" question.
  - One "en_to_cn_production" question.

Type "cn_comprehension":
- "prompt_cn": Chinese question testing understanding of the segment.
- "reference_answer_cn": 1–3 sentence model answer in natural Chinese.
- "reference_answer_en": 1–3 sentence English explanation that closely matches the Chinese answer.

Type "en_to_cn_production":
- "prompt_en": English prompt asking the learner to answer in Chinese.
- "target_answer_cn": 1–3 sentence target answer in natural Chinese.
- "target_answer_en": English paraphrase or translation of the target Chinese answer.

Language constraints:
- No pinyin in any questions or answers.
- Chinese fields must be in simplified Chinese only.
- English fields must be in natural English only.

Output format:
- Respond in VALID JSON only.
- Do NOT include any explanation, comments, or extra text outside the JSON.
- Use snake_case for all keys.
- Root object must have a single key "questions".
- "questions" is an array of question objects.

Input:
- "segment_chinese": the Chinese text of the segment.
- "segment_summary_en": a brief English paraphrase of the segment.

Now read the following input and output the JSON.

SEGMENT_CHINESE:
{segment_chinese}

SEGMENT_SUMMARY_EN:
{segment_summary_en}
""".strip()


def build_cloze_prompt(sentence_cn: str) -> str:
    return f"""
You are a Mandarin teaching assistant creating cloze (fill-in-the-blank) items for advanced (HSK 6) learners from Chinese academic lecture sentences.

Your task:
- Input: one Chinese sentence from a lecture.
- Output: 1–3 cloze questions based on this sentence.

Cloze design rules:
- Each cloze question must be based on the SAME input sentence.
- Each cloze question must have EXACTLY ONE blank.
- Represent the blank with four underscores: "____".
- Focus the blank on meaningful elements:
  - Academic keywords,
  - Important content words,
  - Discourse markers or connectors,
  - Phrases that carry key meaning or stance.
- Avoid making the blank too trivial.

Output format:
- Respond in VALID JSON only.
- Do NOT include any explanation, comments, or extra text outside the JSON.
- Use snake_case for all keys.
- Root object must have a single key "cloze".
- "cloze" is an array of cloze objects.
- Each cloze object must have:
  - "question_cn": the original sentence with ONE part replaced by "____".
  - "answer_cn": the exact Chinese word or phrase that fills the blank.
  - "hint_en": a short English hint.
  - "explanation_en": a short English explanation.

Language constraints:
- "question_cn" and "answer_cn": simplified Chinese only.
- "hint_en" and "explanation_en": natural English only.

Input:
- "sentence_cn": one Chinese sentence from the transcript.

Now read the following input and output the JSON.

SENTENCE_CN:
{sentence_cn}
""".strip()


def build_lecture_summary_prompt(segments: List[Dict[str, Any]]) -> str:
    segments_payload = json.dumps(
        [
            {
                "segment_index": segment["segment_index"],
                "chinese": segment["chinese"],
                "summary_en": segment["summary_en"],
            }
            for segment in segments
        ],
        ensure_ascii=False,
    )
    return f"""
You are an expert summarizer and Mandarin instructor creating lecture-level overviews for an advanced (HSK 6) learner.

Your task:
- Input: a list of segments from one lecture, each with:
  - "segment_index": integer,
  - "chinese": Chinese text of the segment,
  - "summary_en": brief English paraphrase.
- Output: a coherent lecture-level summary in Chinese and English, plus key bilingual takeaways.

Output format:
- Respond in VALID JSON only.
- Do NOT include any explanation, comments, or extra text outside the JSON.
- Use snake_case for all keys.
- Root object must have:
  - "summary_cn": string (3–6 paragraphs of Chinese, paragraphs separated by newlines).
  - "summary_en": string (3–6 paragraphs of English, paragraphs separated by newlines).
  - "takeaways": array of objects with keys "cn" and "en", each a one-sentence statement.

Language constraints:
- "summary_cn" and "takeaways.cn": simplified Chinese only.
- "summary_en" and "takeaways.en": natural English only.

Input:
- "segments": JSON array of objects with keys "segment_index", "chinese", and "summary_en".

Now read the following input and output the JSON.

SEGMENTS_JSON:
{segments_payload}
""".strip()


def main() -> None:
    args = parse_arguments()

    transcript_path = Path(args.transcript_path).expanduser().resolve()
    if not transcript_path.is_file():
        raise SystemExit(f"Transcript file does not exist: {transcript_path}")

    transcript_text = load_transcript(transcript_path)
    lecture_id = args.lecture_id or transcript_path.stem

    api_key = get_api_key()
    api_base = args.api_base
    model = args.model

    # 1) Segment the lecture
    segmentation_prompt = build_segmentation_prompt(transcript_text)
    segmentation_raw = call_llm(
        api_key=api_key,
        api_base=api_base,
        model=model,
        prompt=segmentation_prompt,
    )
    segmentation_data = parse_json_from_llm(segmentation_raw)
    segments: List[Dict[str, Any]] = segmentation_data.get("segments", [])

    # 2–4) For each segment, build vocab, questions, and cloze
    for segment in segments:
        chinese_text = segment.get("chinese", "")
        summary_en = segment.get("summary_en", "")

        vocab_prompt = build_vocab_prompt(
            segment_chinese=chinese_text,
            segment_context=f"Lecture id: {lecture_id}",
        )
        vocab_raw = call_llm(
            api_key=api_key,
            api_base=api_base,
            model=model,
            prompt=vocab_prompt,
        )
        vocab_data = parse_json_from_llm(vocab_raw)

        questions_prompt = build_questions_prompt(
            segment_chinese=chinese_text,
            segment_summary_en=summary_en,
        )
        questions_raw = call_llm(
            api_key=api_key,
            api_base=api_base,
            model=model,
            prompt=questions_prompt,
        )
        questions_data = parse_json_from_llm(questions_raw)

        cloze_prompt = build_cloze_prompt(sentence_cn=chinese_text)
        cloze_raw = call_llm(
            api_key=api_key,
            api_base=api_base,
            model=model,
            prompt=cloze_prompt,
        )
        cloze_data = parse_json_from_llm(cloze_raw)

        segment["vocab"] = vocab_data.get("vocab", [])
        segment["questions"] = questions_data.get("questions", [])
        segment["cloze"] = cloze_data.get("cloze", [])

    # 5) Lecture-level summary
    lecture_summary_prompt = build_lecture_summary_prompt(segments)
    lecture_summary_raw = call_llm(
        api_key=api_key,
        api_base=api_base,
        model=model,
        prompt=lecture_summary_prompt,
    )
    lecture_summary = parse_json_from_llm(lecture_summary_raw)

    # Final combined object
    review: Dict[str, Any] = {
        "lecture_id": lecture_id,
        "transcript_path": str(transcript_path),
        "segments": segments,
        "lecture_summary": lecture_summary,
    }

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{lecture_id}.review.json"
    output_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote bilingual lecture review JSON to: {output_path}")


if __name__ == "__main__":
    main()

