"""Discord bot for querying Cyberpunk 2077 knowledge base using Kedro pipelines."""

import os
import asyncio
import discord
from discord.ext import commands
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.framework.project import configure_project
from pathlib import Path
from typing import Any


# --- Discord setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# --- Discord message length constants ---
DISCORD_MAX_MESSAGE_LENGTH = 2000
DISCORD_SAFE_MESSAGE_LENGTH = 1900


def setup_kedro_project() -> Path:
    """Bootstrap and configure Kedro project.

    Returns:
        Path: The project root path.
    """
    project_path = Path(__file__).resolve().parent
    metadata = bootstrap_project(project_path)
    configure_project(metadata.package_name)
    return project_path


async def send_long_message(ctx: commands.Context, message: str) -> None:
    """Send a message to Discord, chunking if necessary.

    Discord has a maximum message length of 2000 characters. This function
    automatically splits longer messages into multiple chunks to ensure
    all content is delivered.

    Args:
        ctx: Discord command context object.
        message: The message text to send.

    Returns:
        None.
    """
    if len(message) <= DISCORD_SAFE_MESSAGE_LENGTH:
        await ctx.send(message)
    else:
        for i in range(0, len(message), DISCORD_MAX_MESSAGE_LENGTH):
            await ctx.send(message[i : i + DISCORD_MAX_MESSAGE_LENGTH])


@bot.event
async def on_ready() -> None:
    """Event handler called when the bot successfully connects to Discord."""
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")


# --- Help command ---
@bot.command(name="/help")
async def show_help(ctx: commands.Context) -> None:
    """Display all available bot commands in an embedded message.

    Args:
        ctx: Discord command context.

    Returns:
        None.
    """
    embed = discord.Embed(
        title="🤖 Kedro 2077 Bot — Command Guide",
        description="Here's what I can do, choom:",
        color=0x00FFAA,
    )

    embed.add_field(
        name="🧠 `/query <question>`",
        value="Ask me anything about Cyberpunk 2077. I'll run the Kedro LLM pipeline and answer data from the game.",
        inline=False,
    )

    embed.add_field(
        name="🧩 `/build`",
        value="Rebuild the transcript partitions and wiki embeddings. This may take a while — I'll let you know when it's done.",
        inline=False,
    )

    embed.add_field(name="ℹ️ `/help`", value="Show this command list.", inline=False)

    embed.set_footer(text="Powered by Kedro 🔶")

    await ctx.send(embed=embed)


# --- Test if bot exists ---
@bot.command(name="/hello")
async def hello(ctx: commands.Context) -> None:
    """Simple hello command to test if the bot is responding.

    Args:
        ctx: Discord command context.

    Returns:
        None.
    """
    await ctx.send("Hello, I am a bot and I exist! 👋")


# --- Build embeddings and partition transcript ---
@bot.command(name="/build")
async def build_embeddings(ctx: commands.Context) -> None:
    """Run the data processing pipeline asynchronously.

    Rebuilds embeddings from wiki data and partitions the transcript.
    This operation may take several minutes depending on data size.

    Args:
        ctx: Discord command context.

    Returns:
        None.
    """

    await ctx.send(
        "⏳ Building embeddings from wiki and transcript data, please wait..."
    )

    project_path = setup_kedro_project()

    try:
        # Run the blocking Kedro code in a separate thread
        def run_kedro() -> Any:
            with KedroSession.create(project_path=project_path) as session:
                return session.run(pipeline_name="process_transcript")

        await asyncio.to_thread(run_kedro)
        await ctx.send("✅ Embeddings and transcript partitions built successfully!")

    except Exception as e:
        await ctx.send(f"❌ Error running pipeline: {e}")


# --- Query LLM ---
@bot.command(name="/query")
async def run_query(ctx: commands.Context, *, user_query: str) -> None:
    """Run the Kedro query pipeline with a user query asynchronously.

    Processes a user's question about Cyberpunk 2077 by running the Kedro
    query pipeline, which retrieves relevant context and generates an
    LLM response.

    Args:
        ctx: Discord command context.
        user_query: The user's question about Cyberpunk 2077.

    Returns:
        None.
    """

    await ctx.send(f"🚀 Running Kedro pipeline for query: `{user_query}`...\n\n")

    project_path = setup_kedro_project()

    try:
        # Run the blocking Kedro code in a separate thread
        def run_kedro() -> Any:
            with KedroSession.create(
                project_path=project_path, runtime_params={"user_query": user_query}
            ) as session:
                return session.run(pipeline_name="query_pipeline", tags=["discord"])

        result = await asyncio.to_thread(run_kedro)

        # Extract LLM node output
        llm_memory_dataset = result.get("llm_response_discord")
        if llm_memory_dataset:
            llm_response = llm_memory_dataset.load()
            await send_long_message(ctx, llm_response)
        else:
            await ctx.send("⚠️ No response returned by the LLM.")

    except Exception as e:
        await ctx.send(f"❌ Error running pipeline: {e}")


# --- Run the bot ---
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise EnvironmentError("DISCORD_TOKEN not set")
    bot.run(token)
