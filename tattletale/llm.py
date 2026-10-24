"""OpenAI-compatible chat client for a thinking model served by vLLM.

Configured by environment variables:
    LLM_BASE_URL          e.g. http://localhost:8000/v1
    LLM_API_KEY           the server's --api-key
    LLM_MODEL             served model name (default Qwen/Qwen3.8-27B)
    LLM_REASONING_EFFORT  low | medium | xhigh (default low; the model's own default is xhigh)
    LLM_MAX_TOKENS        cap on reasoning + answer per call (default 8192)

The server must split the reasoning trace from the answer (vllm serve --reasoning-parser qwen3),
so `content` holds only the answer and `reasoning` the trace.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

TRANSIENT = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)


@dataclass
class Reply:
    content: str
    reasoning: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    seconds: float
    error: Optional[str] = None


class LLM:
    def __init__(self):
        self.client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ.get("LLM_API_KEY", "EMPTY"),
                             timeout=600)
        self.model = os.environ.get("LLM_MODEL", "Qwen/Qwen3.8-27B")
        self.effort = os.environ.get("LLM_REASONING_EFFORT", "low")
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "8192"))

    def chat(self, prompt: str) -> Reply:
        start = time.time()
        last_error = None
        for attempt in range(4):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    # Model card's thinking-mode sampling.
                    temperature=1.0, top_p=0.95,
                    extra_body={"top_k": 20, "repetition_penalty": 1.0,
                                "chat_template_kwargs": {"enable_thinking": True,
                                                         "reasoning_effort": self.effort}},
                )
                choice = completion.choices[0]
                msg = choice.message
                return Reply(
                    content=(msg.content or "").strip(),
                    reasoning=getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or "",
                    prompt_tokens=completion.usage.prompt_tokens,
                    completion_tokens=completion.usage.completion_tokens,
                    finish_reason=choice.finish_reason or "",
                    seconds=round(time.time() - start, 2),
                )
            except TRANSIENT as e:
                last_error = f"{type(e).__name__}: {e}"
                time.sleep(2 ** attempt)
        return Reply("", "", 0, 0, "error", round(time.time() - start, 2), error=last_error)
