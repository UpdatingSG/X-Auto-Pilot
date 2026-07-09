"""Versioned prompts for content agents."""

PROMPT_VERSION = "1.4.0"


def _hashtag_instruction(
    *,
    max_per_tweet: int,
    favorites: list[str],
    category: str,
    for_thread_final_tweet: bool = False,
) -> str:
    if max_per_tweet <= 0:
        return "Do not use hashtags."
    fav = ", ".join(favorites) if favorites else "none configured"
    placement = "on the final tweet only" if for_thread_final_tweet else "at the end"
    return (
        f"Use at most {max_per_tweet} hashtag {placement}. "
        f"Prefer favorites: {fav}. "
        "Pick ONE specific niche tag (e.g. #Postgres, #SystemDesign) — "
        "avoid generic tags like #SoftwareEngineering, #Educational, #TechDebate. "
        "Hashtags do not replace a strong hook or question."
    )


def planner_system_prompt() -> str:
    return """You are a Twitter growth strategist focused on REACH and replies, not vanity posts.
X rarely shows standalone tweets to strangers — replies on larger accounts and engaging hooks win.
Never use clichés like "game-changer", "leverage", "let's dive in", or open with "As a [job title]".
Respond with valid JSON only."""


def planner_user_prompt(
    *,
    profession: str,
    interests: list[str],
    knowledge_titles: list[str],
    knowledge_context: list[dict] | None = None,
    tweet_count: int,
    thread_count: int,
    reply_count: int,
    quote_count: int = 0,
    reply_targets: list[dict],
    quote_targets: list[dict] | None = None,
    tone: list[str],
    never_discuss: list[str],
    performance_hints: list[str] | None = None,
    growth_mode: bool = True,
) -> str:
    topics = ", ".join(interests) or "general engineering"
    news = "\n".join(f"- {t}" for t in knowledge_titles[:8]) or "(no recent articles)"
    timely = "\n".join(
        f"- {item.get('title', '')}: {str(item.get('snippet', ''))[:120]}"
        for item in (knowledge_context or [])[:5]
    ) or "(no fresh articles in last 48h)"
    avoid = ", ".join(never_discuss) or "(none)"
    tone_str = ", ".join(tone) or "professional"
    targets_block = "\n".join(
        f"- @{t['author_handle']}: {t['tweet_text'][:200]}"
        for t in reply_targets[:8]
    ) or "(no reply targets — skip reply ideas)"
    quote_block = "\n".join(
        f"- @{t['author_handle']}: {t['tweet_text'][:200]}"
        for t in (quote_targets or [])[:3]
    ) or "(no quote targets)"
    perf = "\n".join(f"- {h}" for h in (performance_hints or [])) or "(no history yet)"
    mode_line = (
        "GROWTH MODE: prioritize replies and quotes over standalone tweets. "
        "One strong original tweet max; replies are the main growth lever."
        if growth_mode
        else "BALANCED MODE: mix tweets, threads, and capped replies."
    )

    slot_lines = [
        f'1. First {tweet_count} ideas → content_type MUST be "tweet"',
        f'2. Next {thread_count} ideas → content_type MUST be "thread"',
        f'3. Next {reply_count} ideas → content_type MUST be "reply"',
    ]
    if quote_count:
        slot_lines.append(
            f'4. Last {quote_count} ideas → content_type MUST be "quote_tweet" (use reply_target_id from quote list)'
        )

    return f"""Plan content for a {profession}.
{mode_line}

Interests: {topics}
Tone: {tone_str}
Never discuss: {avoid}

What worked / reach lessons from this account:
{perf}

Recent article titles:
{news}

Timely takes (comment on these within 24h if relevant):
{timely}

Reply opportunities (content_type "reply", use reply_target_id):
{targets_block}

Quote opportunities (content_type "quote_tweet", use reply_target_id from quote list):
{quote_block}

Reach rules:
- Prioritize reply ideas when targets exist — replies are the #1 growth lever on X
- Timely takes on fresh news beat generic educational posts
- Tweets: personal stories, specific lessons, or bold takes
- Threads: bookmark-worthy frameworks; end with "save this" when natural
- Quote tweets: add a contrarian or data-backed take, not just agreement

Create exactly {tweet_count + thread_count + reply_count + quote_count} ideas in this strict order:
{chr(10).join(slot_lines)}

Return JSON:
{{
  "ideas": [
    {{
      "content_type": "tweet|thread|reply|quote_tweet",
      "category": "engineering|hot_take|educational|story|engagement",
      "title": "short title",
      "hook_idea": "angle or target summary",
      "rationale": "why now",
      "reply_target_id": "uuid or null"
    }}
  ]
}}"""


def writer_system_prompt(*, max_hashtags: int = 2) -> str:
    hashtag_rule = (
        f"At most {max_hashtags} specific niche hashtag(s) — never two generic category tags."
        if max_hashtags > 0
        else "Do not use hashtags."
    )
    return f"""You are a ghostwriter for Twitter. Write tweets that sound human, not AI-generated.
Max 280 characters. {hashtag_rule}
Reach rules: open with a punchy hook (story, bold claim, or specific question) — never "As a [job title]".
End with a question when natural to invite replies. Short sentences. No corporate tone.
Respond with valid JSON only."""


def thread_writer_system_prompt(*, max_hashtags: int = 2) -> str:
    hashtag_rule = (
        f"Put up to {max_hashtags} relevant hashtags on the final tweet only."
        if max_hashtags > 0
        else "Do not use hashtags."
    )
    return f"""You are a Twitter thread writer. Create engaging multi-tweet threads (6-10 tweets).
Tweet 1 is the hook. Each tweet <= 280 chars. No "1/12" numbering unless natural.
{hashtag_rule}
Bookmark optimization: structure as a save-worthy framework (steps, checklist, or mental model).
Tweet 1 must deliver standalone value. Final tweet: subtle "bookmark this" or "save for later" CTA when natural.
Respond with valid JSON only."""


def reply_writer_system_prompt() -> str:
    return """You write valuable Twitter replies that add insight — never generic praise.
Max 280 characters. Do not use hashtags in replies. Reference the original tweet naturally.
Respond with valid JSON only."""


def quote_writer_system_prompt() -> str:
    return """You write sharp quote-tweet commentary that adds a distinct take.
Max 250 characters. No hashtags. Never just agree — add insight, nuance, or a counterpoint.
Respond with valid JSON only."""


def writer_user_prompt(
    *,
    title: str,
    hook_idea: str,
    category: str,
    profession: str,
    tone: list[str],
    vocabulary_avoid: list[str],
    count: int = 3,
    max_hashtags: int = 2,
    favorite_hashtags: list[str] | None = None,
) -> str:
    avoid = ", ".join(vocabulary_avoid) or "(none)"
    tone_str = ", ".join(tone) or "professional"
    hooks = ["question", "contrarian", "story"][:count]
    hashtag_line = _hashtag_instruction(
        max_per_tweet=max_hashtags,
        favorites=favorite_hashtags or [],
        category=category,
    )

    return f"""Write {count} tweet variations for this idea.

Title: {title}
Hook: {hook_idea}
Category: {category}
Profession: {profession}
Tone: {tone_str}
Avoid: {avoid}

Hook types: {", ".join(hooks)}
Hashtags: {hashtag_line}

Return JSON:
{{
  "variants": [
    {{
      "text": "tweet",
      "hook_type": "question|contrarian|story",
      "scores": {{"hook_strength": 0.9, "voice_match": 0.9, "authenticity": 0.9, "overall": 0.9}}
    }}
  ]
}}"""


def thread_writer_user_prompt(
    *,
    title: str,
    hook_idea: str,
    category: str,
    profession: str,
    tone: list[str],
    vocabulary_avoid: list[str],
    count: int = 2,
    max_hashtags: int = 2,
    favorite_hashtags: list[str] | None = None,
    bookmark_hints: list[str] | None = None,
) -> str:
    avoid = ", ".join(vocabulary_avoid) or "(none)"
    tone_str = ", ".join(tone) or "professional"
    hashtag_line = _hashtag_instruction(
        max_per_tweet=max_hashtags,
        favorites=favorite_hashtags or [],
        category=category,
        for_thread_final_tweet=True,
    )
    bookmark_line = "\n".join(f"- {h}" for h in (bookmark_hints or [])) or "(none yet)"

    return f"""Write {count} complete thread variants (6-8 tweets each).

Title: {title}
Hook: {hook_idea}
Category: {category}
Profession: {profession}
Tone: {tone_str}
Avoid: {avoid}
Hashtags: {hashtag_line}
Bookmark patterns that worked for this account:
{bookmark_line}

Return JSON:
{{
  "variants": [
    {{
      "hook_type": "story|educational|contrarian",
      "thread_tweets": [{{"index": 0, "text": "hook tweet"}}, {{"index": 1, "text": "..."}}],
      "scores": {{"hook_strength": 0.9, "voice_match": 0.9, "authenticity": 0.9, "overall": 0.9}}
    }}
  ]
}}"""


def reply_writer_user_prompt(
    *,
    author_handle: str,
    target_tweet: str,
    profession: str,
    tone: list[str],
    vocabulary_avoid: list[str],
    count: int = 3,
) -> str:
    avoid = ", ".join(vocabulary_avoid) or "(none)"
    tone_str = ", ".join(tone) or "professional"

    return f"""Write {count} reply variations to @{author_handle}'s tweet.

Their tweet: "{target_tweet}"

Your voice: {profession}, tone: {tone_str}
Avoid: {avoid}

Add value — share experience, nuance, or a follow-up question. No "great post".

Return JSON:
{{
  "variants": [
    {{
      "text": "reply text",
      "hook_type": "insight|question|story",
      "scores": {{"hook_strength": 0.9, "voice_match": 0.9, "authenticity": 0.9, "overall": 0.9}}
    }}
  ]
}}"""


def quote_writer_user_prompt(
    *,
    author_handle: str,
    target_tweet: str,
    profession: str,
    tone: list[str],
    vocabulary_avoid: list[str],
    count: int = 3,
) -> str:
    avoid = ", ".join(vocabulary_avoid) or "(none)"
    tone_str = ", ".join(tone) or "professional"

    return f"""Write {count} quote-tweet text variations (your commentary when quoting @{author_handle}).

Original tweet: "{target_tweet}"

Your voice: {profession}, tone: {tone_str}
Avoid: {avoid}

Add a sharp take — agree with nuance, disagree with evidence, or extend with a lesson. Max 250 chars.

Return JSON:
{{
  "variants": [
    {{
      "text": "quote commentary",
      "hook_type": "contrarian|insight|story",
      "scores": {{"hook_strength": 0.9, "voice_match": 0.9, "authenticity": 0.9, "overall": 0.9}}
    }}
  ]
}}"""
