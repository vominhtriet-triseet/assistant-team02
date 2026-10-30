# Optional AI provider: local model or API key

The assistant works without any AI. Rules read tasks, dates, durations, and study time,
and they are tested in `tests/`. A language model is only used when the rules find
nothing in a message that looks like a planning request (it mentions a plan, schedule,
deadline, exam, homework, and so on). The model returns JSON, and
`service._tasks_from_llm()` checks every field: titles must be text, deadlines must be
real dates, hours must be between 0 and 40. Anything else is dropped. If the model is
unreachable, the assistant says so and keeps working with rules only.

Choose the provider with environment variables, or copy `.env.example` to `.env` in the
repository root and edit it. `.env` is ignored by Git, so keys are not committed.

## Option 1: local model with Ollama

Nothing leaves the computer and there is no cost per message.

What you need:

| Item | Notes |
|---|---|
| [Ollama](https://ollama.com/download) | Installs a local model server on Windows, macOS, or Linux and listens on `http://localhost:11434`. |
| A small instruction model | For example `qwen2.5:3b` (about 2 GB). Larger models such as `qwen2.5:7b` read requests better but need more memory. |
| Hardware | About 8 GB RAM for a 3B model on CPU. A GPU with 6 GB or more VRAM makes replies much faster. Replies on CPU can take several seconds. |

Steps:

```bash
ollama pull qwen2.5:3b
```

Then set in `.env`:

```text
ASSISTANT_LLM=ollama
ASSISTANT_LLM_MODEL=qwen2.5:3b
```

Start the assistant with `python -m assistant serve`. The first line printed shows
`AI provider: ollama`. `GET /api/health` also reports the provider.

## Option 2: an API key

Faster and more accurate than a small local model, but messages are sent to the
provider, each call costs money (some providers have a free tier), and you need an
internet connection.

What you need:

| Item | Notes |
|---|---|
| An account and API key from a provider with an OpenAI-compatible Chat Completions endpoint | OpenAI, Groq, OpenRouter, Google Gemini (OpenAI-compatible endpoint), or a local LM Studio server all work with the same code. |
| The provider's base URL and a model name | Copy both from the provider's documentation. The model must support JSON output (`response_format: json_object`). |

Set in `.env`:

```text
ASSISTANT_LLM=openai
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-key
ASSISTANT_LLM_MODEL=a-model-name-from-your-provider
```

Keep the key out of Git, screenshots, and the report. Use synthetic data in demos, as
the project report requires.

## Which one to choose

| | Local (Ollama) | API key |
|---|---|---|
| Cost | Free after download | Pay per use or free tier limits |
| Privacy | Data stays on the machine | Messages go to the provider |
| Quality | Good enough for short English requests with a 3B to 7B model | Better on long or mixed-language requests |
| Speed | Depends on your hardware | Usually fast |
| Offline demo | Works | Needs internet |

For the course demo, run without AI first: the planning flow is fully rule-based. Turn
on Ollama to show how unusual requests are handled, and mention that the model only
proposes data that the application validates.
