"""
Google ADK - 4. ParallelAgent (fan-out, then gather)
Five specialist agents research and write at the same time, then one agent
merges their work into a single content plan.

Run from the "12. ADK" folder:
    adk web                    (then pick agent_4_parallel in the dropdown)
    adk run agent_4_parallel   (chat in the terminal)

Needs GOOGLE_API_KEY in the .env file at the repo root.
"""

from dotenv import load_dotenv
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search

load_dotenv()

# "gemini-flash-latest" always points to the current Flash model - pinned
# versions (e.g. "gemini-2.0-flash") get retired and start returning 404s
AGENT_MODEL = "gemini-flash-latest"


# --- The specialists ---
# They don't depend on each other, so they can run in parallel. Each one saves
# its result into session state under its own output_key.

# Blog Content Writer Agent with Trend Analysis
blog_writer_agent = Agent(
    name="TrendAwareBlogWriterAgent",
    model=AGENT_MODEL,
    tools=[google_search],
    description="An agent that creates trend-aware blog content using comprehensive trend research",
    instruction="""
    You are a professional blog writer with expertise in trend analysis. Given a topic, you will:

    1. TREND RESEARCH (run these 3 searches):
       - The topic + "trends this year"
       - The topic + "latest news industry updates"
       - The topic + "viral content social media"

    2. BLOG CREATION:
       - Write a comprehensive, trend-aware blog post (800-1200 words)
       - Incorporate trending topics and keywords naturally
       - Reference recent industry developments
       - Structure for SEO with compelling headlines
       - Add current statistics and facts from research

    Always base your content on real trend data you discover through your searches.
    Make the content feel current, relevant, and backed by actual trending insights.
    """,
    output_key="blog_content",
)

# SEO Specialist Agent with Trend Research
seo_specialist_agent = Agent(
    name="TrendAwareSEOAgent",
    model=AGENT_MODEL,
    tools=[google_search],
    description="An agent that creates SEO strategies based on current trends and competitor analysis",
    instruction="""
    You are an SEO specialist who excels at trend-based keyword research. For the given topic, you will:

    1. KEYWORD AND COMPETITOR RESEARCH (run these 3 searches):
       - The topic + "trending keywords this year"
       - "What people search for" + the topic
       - The topic + "top performing content SEO"

    2. SEO STRATEGY CREATION:
       - High-value trending keywords and long-tail search terms
       - SEO-optimized titles and meta descriptions
       - Content structure recommendations based on top performers
       - Internal and external linking opportunities
       - Competitor gap analysis and opportunities

    Focus on leveraging current search trends for maximum visibility.
    """,
    output_key="seo_strategy",
)

# Visual Content Creator Agent with Viral Pattern Analysis
visual_creator_agent = Agent(
    name="TrendAwareVisualAgent",
    model=AGENT_MODEL,
    tools=[google_search],
    description="An agent that creates visual content strategies based on viral patterns and visual trends",
    instruction="""
    You are a visual content strategist who identifies viral visual patterns. For the given topic, you will:

    1. VIRAL VISUAL RESEARCH (run these 3 searches):
       - The topic + "viral videos trending formats"
       - The topic + "Instagram TikTok viral content"
       - The topic + "infographic trending designs"

    2. VISUAL STRATEGY CREATION:
       - Trending visual formats and styles for each platform
       - Specific image and video concepts based on viral patterns
       - Color schemes and design trends currently popular
       - Seasonal visual themes and a short visual content calendar

    Base all recommendations on actual viral patterns you discover through research.
    """,
    output_key="visual_content",
)

# Social Media Manager Agent with Engagement Analysis
social_media_agent = Agent(
    name="TrendAwareSocialAgent",
    model=AGENT_MODEL,
    tools=[google_search],
    description="An agent that creates social media strategies based on viral patterns and engagement trends",
    instruction="""
    You are a social media expert who analyzes viral content patterns. For the given topic, you will:

    1. VIRAL CONTENT RESEARCH (run these 4 searches):
       - The topic + "viral social media posts this year"
       - The topic + "trending hashtags Instagram Twitter"
       - The topic + "TikTok trending challenges"
       - The topic + "influencer collaboration trends"

    2. SOCIAL STRATEGY CREATION:
       - Platform-specific content based on viral patterns
       - Trending hashtags and optimal posting times
       - Content formats that drive highest engagement
       - Influencer collaboration opportunities
       - Community engagement and growth tactics

    Create strategies that leverage proven viral patterns and engagement techniques.
    """,
    output_key="social_strategy",
)

# Email Marketing Agent with Industry Trend Analysis
email_marketing_agent = Agent(
    name="TrendAwareEmailAgent",
    model=AGENT_MODEL,
    tools=[google_search],
    description="An agent that creates email marketing campaigns based on industry trends and best practices",
    instruction="""
    You are an email marketing specialist who stays current with industry trends. For the given topic, you will:

    1. EMAIL TREND RESEARCH (run these 3 searches):
       - The topic + "email marketing trends this year"
       - The topic + "email subject lines high open rates"
       - The topic + "email campaign examples successful"

    2. EMAIL STRATEGY CREATION:
       - Subject lines incorporating trending topics and industry news
       - Newsletter themes that align with industry trends
       - Lead magnets based on trending interests
       - An email sequence outline
       - Segmentation strategies based on current behavior trends

    Create email campaigns that feel timely, relevant, and based on current industry insights.
    """,
    output_key="email_campaigns",
)

# --- Fan-out ---
# A ParallelAgent starts all sub_agents at the same time and waits for every one
# to finish. Like SequentialAgent, it is not an LLM itself. The sub-agents don't
# see each other's work while they run.
parallel_research_agent = ParallelAgent(
    name="ParallelContentResearch",
    description="Runs the five content specialists at the same time",
    sub_agents=[
        blog_writer_agent,
        seo_specialist_agent,
        visual_creator_agent,
        social_media_agent,
        email_marketing_agent,
    ],
)

# --- Gather ---
# Runs after all specialists are done and reads their results from session state
content_merger_agent = Agent(
    name="ContentPlanMergerAgent",
    model=AGENT_MODEL,
    description="An agent that combines the specialists' work into one content plan",
    instruction="""
    You are a content director. Combine the work of your team into one clear,
    consistent content plan. Remove duplicates and make sure the keywords, visuals,
    social posts and emails all support the blog post.

    BLOG POST:
    {blog_content}

    SEO STRATEGY:
    {seo_strategy}

    VISUAL CONTENT:
    {visual_content}

    SOCIAL MEDIA STRATEGY:
    {social_strategy}

    EMAIL CAMPAIGNS:
    {email_campaigns}

    Format the final output as:

    BLOG POST: [the final blog post, with the SEO title and meta description]

    SEO: [top keywords and structure recommendations]

    VISUALS: [the key visual concepts per platform]

    SOCIAL MEDIA: [posts, hashtags and posting times per platform]

    EMAIL: [subject lines and the campaign outline]
    """,
)

# ==== Main System ====
# Parallel inside sequential: fan out to the specialists, then gather with the merger
root_agent = SequentialAgent(
    name="TrendAwareContentCreationSystem",
    description="A comprehensive content creation system that uses real-time trend monitoring to create data-driven, current content across all channels",
    sub_agents=[parallel_research_agent, content_merger_agent],
)
