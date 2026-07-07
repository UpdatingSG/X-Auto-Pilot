"""Versioned prompts for content agents."""

PROMPT_VERSION = "1.2.0"


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
    placement = "on the final tweet only" if for_thread_final_tweet else "at the end of each tweet"
    return (
        f"Include {max_per_tweet} relevant hashtag(s) {placement} for discoverability. "
        f"Prefer favorites when set: {fav}. "
        f"Otherwise pick specific tags for category '{category}' (avoid generic tags like #motivation)."
    )


def planner_system_prompt() -> str:
    return """You are a Twitter growth strategist. Plan a balanced mix of tweets, threads, and reply opportunities.
Never use clichés like "game-changer", "leverage", "let's dive in".
Respond with valid JSON only."""


def planner_user_prompt(
    *,
    profession: str,
    interests: list[str],
    knowledge_titles: list[str],
    tweet_count: int,
    thread_count: int,
    reply_count: int,
    reply_targets: list[dict],
    tone: list[str],
    never_discuss: list[str],
) -> str:
    topics = ", ".join(interests) or "general engineering"
    news = "\n".join(f"- {t}" for t in knowledge_titles[:8]) or "(no recent articles)"
    avoid = ", ".join(never_discuss) or "(none)"
    tone_str = ", ".join(tone) or "professional"
    targets_block = "\n".join(
        f"- @{t['author_handle']}: {t['tweet_text'][:200]}"
        for t in reply_targets[:5]
    ) or "(no reply targets — skip reply ideas)"

    return f"""Plan content for a {profession}.

Interests: {topics}
Tone: {tone_str}
Never discuss: {avoid}

Recent articles:
{news}

Reply opportunities (use content_type "reply" with matching reply_target_id):
{targets_block}

Create exactly {tweet_count + thread_count + reply_count} ideas in this strict order:
1. First {tweet_count} ideas → content_type MUST be "tweet" (single posts, hooks, hot takes)
2. Next {thread_count} ideas → content_type MUST be "thread" (deep dives, 6-10 tweet arcs)
3. Last {reply_count} ideas → content_type MUST be "reply" (must use reply_target_id from list above)

Do NOT label every idea as a thread. Tweets are the majority of the plan.

Return JSON:
{{
  "ideas": [
    {{
      "content_type": "tweet|thread|reply",
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
        f"Include up to {max_hashtags} relevant hashtags at the end when they fit naturally."
        if max_hashtags > 0
        else "Do not use hashtags."
    )
    return f"""You are a ghostwriter for Twitter. Write tweets that sound human, not AI.
Max 280 characters per tweet. {hashtag_rule}
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
Respond with valid JSON only."""


def reply_writer_system_prompt() -> str:
    return """You write valuable Twitter replies that add insight — never generic praise.
Max 280 characters. Do not use hashtags in replies. Reference the original tweet naturally.
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
) -> str:
    avoid = ", ".join(vocabulary_avoid) or "(none)"
    tone_str = ", ".join(tone) or "professional"
    hashtag_line = _hashtag_instruction(
        max_per_tweet=max_hashtags,
        favorites=favorite_hashtags or [],
        category=category,
        for_thread_final_tweet=True,
    )

    return f"""Write {count} complete thread variants (6-8 tweets each).

Title: {title}
Hook: {hook_idea}
Category: {category}
Profession: {profession}
Tone: {tone_str}
Avoid: {avoid}
Hashtags: {hashtag_line}

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
