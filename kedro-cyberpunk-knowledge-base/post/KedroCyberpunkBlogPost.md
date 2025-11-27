# Building a cyberpunk 2077 knowledge base with Kedro and LangChain

There's a well-known adage about writing that tells people to "write what they know." When I had to create a project to test an experimental Kedro dataset for loading LangChain prompt templates, I decided to take that advice to heart.

I embarked upon the nerdy endeavor of building an LLM-powered question-answering knowledge base whose sole purpose is to accurately answer questions about the action role-playing game Cyberpunk 2077. With over 400 hours of gameplay, every achievement unlocked, and more than a few passionate discussions (read: heated arguments on Reddit) about the game under my belt, this would be the perfect test subject. I could easily spot inaccurate responses, hallucinations, or any other LLM quirks that might slip through.

To my pleasant surprise, this project would evolve to become a valuable learning experience in building data pipelines with Kedro, wrestling with LLM limitations, and discovering that sometimes the best solutions come from working within constraints rather than around them.

## The project

At its core, this is a Retrieval-Augmented Generation (RAG) system built with Kedro. The initial goal was to take a full transcript of a Cyberpunk 2077 playthrough (over 400 pages of dialog), make it searchable, and use it to answer questions accurately. I could only select a specific playthrough on a blog that transcribes games (linked below), and this was a challenge seeing as the game itself has multiple different endings based on the player's choices throughout the story.

## The transcript

The `LangChainPromptDataset` was built to seamlessly integrate LangChain `PromptTemplate` objects into Kedro pipelines, allowing prompts to be loaded as raw data files and reducing boilerplate code. For a proper field test, I wanted to use it with a real LLM query workflow, not just unit tests or mock responses.

### Let's talk about chunking...

When I started, the first issue I encountered was that LLMs have token limits. You can't just dump 400 pages of transcript into a prompt and expect it to work. The transcript needed to be broken down into manageable chunks.

I started by creating a `process_transcript` Kedro pipeline that handles this transformation:

```python
def chunk_transcript(
    transcript: str, chunk_size: int = 1000, overlap: int = 200
) -> List[Dict[str, Any]]:
    """Split transcript into overlapping chunks for context retrieval."""
    cleaned_transcript = re.sub(r"\n+", "\n", transcript.strip())
    sentences = re.split(r"(?<=[.!?])\s+", cleaned_transcript)

    chunks = []
    start_idx = 0

    while start_idx < len(sentences):
        end_idx = min(start_idx + chunk_size, len(sentences))
        chunk_text = " ".join(sentences[start_idx:end_idx])

        chunks.append({
            "text": chunk_text,
            "chunk_id": len(chunks),
            "start_sentence": start_idx,
            "end_sentence": end_idx - 1,
        })

        # Move forward with overlap to preserve context
        start_idx = max(start_idx + chunk_size - overlap, start_idx + 1)

    return chunks
```

The overlap is crucial as it ensures that context spanning chunk boundaries isn't lost. This is a common pattern in RAG systems, but implementing it as a Kedro node made it easy to experiment with different chunk sizes and overlap values through the pipeline `parameters` feature.

Then I built the project into two separate pipelines:

1. **`process_transcript`**: Processes raw data once (expensive operation)
2. **`query_pipeline`**: Runs queries repeatedly (cheap operation)

Kedro's pipeline structure made iteration easier. This separation meant I could process the data once, store it as a Kedro dataset, and then query it as many times as I wanted without reprocessing. The data catalog handles all the file I/O, so storage and loading are straightforward.

### Chippin' in: the challenges after chunking

The transcript itself led to four fundamental limitations:

1. **Dialog-only content**: The 400-page transcript contained only dialog, missing crucial narrative context about what's actually happening in scenes.

2. **Single playthrough bias**: As I've mentioned earlier, Cyberpunk 2077 is a game where player choices dramatically alter the story. This transcript was from only one specific playthrough, so it didn't have information about alternative paths or endings.

3. **The hallucination problem**: When I instructed the LLM to strictly use only the provided context with a low temperature, it would often respond with "I don't have sufficient information." But if I allowed it more freedom or increased the temperature, it would confidently spout misinformation about the game.

4. **Naive keyword matching**: My initial approach of using simple keyword matching to find relevant chunks was inadequate. Sometimes completely unrelated chunks would be selected, leading to nonsensical responses about other plot points or characters. What a gonk.

### Preem solutions

Kedro's node-based architecture made it trivial to experiment with different approaches. Each solution became a new node or a modification to an existing one.

**Solution 1: PartitionedDataset for better retrieval**

I initially stored chunks as individual JSON files. Switching to Kedro's `PartitionedDataset` made retrieval more efficient and the code cleaner:

```python
def partition_transcript_chunks(
    chunks: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Convert chunks into partition mapping for Kedro's PartitionedDataset."""
    partitions: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", len(partitions))
        partition_key = f"chunk_{chunk_id}"
        partitions[partition_key] = chunk
    return partitions
```

This change alone improved response quality because the partitioned structure made it easier to search and retrieve specific chunks.

**Solution 2: Character name extraction**

The transcript's "Character: Dialogue" structure made it easy to extract character names:

```python
def extract_characters(transcript: str) -> List[str]:
    """Extract unique character names from transcript (format: "Name: Dialogue")."""
    character_pattern = r"^([A-Za-z\s]+):"
    characters = set()
    
    for line in transcript.split("\n"):
        match = re.match(character_pattern, line.strip())
        if match:
            character_name = match.group(1).strip()
            if character_name and len(character_name) > 1:
                characters.add(character_name)
    
    return sorted(list(characters))
```

I used this character list to boost the relevance score of transcript chunks when a query mentioned a character name. This simple heuristic significantly improved results for character-related questions.

**Solution 3: Semantic similarity with Sentence Transformers**

The most notable improvement came when I replaced keyword matching with semantic similarity search using Sentence Transformers:

```python
def find_relevant_contexts(
    query: str,
    transcript_chunks: Dict[str, Any],
    wiki_embeddings: Dict[str, Dict[str, Any]],
    character_list: List[str],
    embedding_model_name: str = "all-MiniLM-L6-v2",
    max_chunks: int = 5,
    character_bonus: float = 0.05,
    wiki_weight: float = 0.7,
) -> List[Dict[str, Any]]:
    """Retrieve top relevant contexts using semantic similarity."""
    model = get_embedding_model(embedding_model_name)
    query_emb = model.encode(query, convert_to_tensor=True)
    
    results = []
    # Calculate similarity for transcript chunks and wiki pages...
    # Apply character bonus and wiki weight...
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [
        {"source": src, "text": txt, "similarity": sim}
        for sim, src, txt in results[:max_chunks]
    ]
```

This change made response quality significantly better. The model could now understand that "Who is Johnny Silverhand?" and "Tell me about the guy who blew up Arasaka Tower" were asking for similar information, even without exact keyword matches.

However, even with these improvements, the transcript alone was insufficient. Questions about characters worked reasonably well, but questions about game mechanics, missions, or world-building fell flat. The data simply wasn't there. I needed a better data source.

## The wiki

I needed a source of data that was complete, up-to-date, reliable, and neutral because people get *very* passionate about their in-game choices. The community-maintained Cyberpunk Wiki was the obvious answer.

### The download challenge

The wiki is substantial, as it's about 15,000 pages. Downloading it required:

1. **Respecting API rate limits**: I had to add intentional pauses between requests to avoid getting blocked. The download script took a couple of hours to complete.

2. **Choosing the right format**: I settled on a single JSON file where each page is a key-value pair:

   ```json
   {
     "Johnny Silverhand": "Johnny Silverhand is a...",
     "Arasaka Tower": "Arasaka Tower is located in...",
     ...
   }
   ```

   This format made it easy to process in Kedro and convert to embeddings.

3. **Data cleanup**: A significant portion of the work was cleaning the data:

   * Removing redirect pages
   * Stripping Markdown syntax
   * Removing image tags, external links, and language links
   * Cleaning up formatting artifacts

I wrote a separate Python script for this cleanup, which was a one-time operation. The cleaned data went into the `data/raw/` directory, ready for Kedro to process.

### Kedro-specific challenges

This project was already testing one new dataset (`LangChainPromptDataset`), and I wanted to see how far I could push Kedro's built-in datasets before needing external tools.

The "proper" solution for storing embeddings would be a vector database like Pinecone or Weaviate. But that would require:

1. Writing another custom dataset to interface with the database
2. Setting up and managing external infrastructure
3. Adding complexity to the project

I decided to test Kedro's limits instead. Could I build a functional RAG system using only Kedro's built-in datasets?

I stored the cleaned wiki data (about 13,000 entries) in a `JSONDataset`, then added a node to the `process_transcript` pipeline to generate embeddings:

```python
def embed_wiki_pages(
    wiki_data: Dict[str, str], 
    embedding_model_name: str = "all-MiniLM-L6-v2"
) -> Dict[str, Dict[str, Any]]:
    """Generate embeddings for wiki pages using SentenceTransformer."""
    model = get_embedding_model(embedding_model_name)
    embedded_pages: Dict[str, Dict[str, Any]] = {}

    for title, text in tqdm(wiki_data.items()):
        if not text.strip():
            continue
        embedding = model.encode(text, convert_to_numpy=True)
        embedded_pages[title] = {"text": text, "embedding": embedding}

    return embedded_pages
```

Then I stored these embeddings in a `PickleDataset`:

```yaml
wiki_embeddings:
  type: pickle.PickleDataset
  filepath: data/processed/wiki_embeddings.pkl
```

This approach has trade-offs:

* ✅ No external dependencies
* ✅ Fast retrieval (everything in memory)
* ✅ No type conversion needed
* ❌ Not scalable for very large datasets
* ❌ Entire dataset loads into memory

For 13,000 pages (about 11 megabytes of data), I decided this was a perfectly reasonable trade-off. The embeddings load quickly, and the similarity search is fast enough for interactive use. It's not production-ready for millions of documents, but it proves that Kedro's built-in tools can handle non-trivial workloads well enough.

### The results

Integrating wiki embeddings into the context retrieval node significantly improved the quality of the output. The system could now answer questions about:

* Characters and locations
* Narrative events and mission outcomes
* Game mechanics like weapons, systems, skills, or vehicles
* World-building and lore

The prompt engineering also became more effective. With better data, I could confidently instruct the LLM to use only the provided context:

```json
{
  "role": "system",
  "content": "You are an expert in Cyberpunk 2077... Using ONLY the information provided from in-game transcripts and wiki entries, answer the user's questions. Do NOT include any information that is not present in the provided context."
}
```

Previously, this strict instruction led to many "I don't have sufficient data" responses. Now, with comprehensive wiki data, the LLM had enough context to provide accurate, detailed answers while staying within the provided materials.

## Making it a conversation

At this point, I had a working RAG system, but using it was clunky. Each query required:

1. Starting a new Kedro session
2. Running the entire pipeline
3. Passing the query as a runtime parameter: `kedro run --pipeline=query_pipeline --params=user_query="Who is Johnny Silverhand?"`

This was fine for testing but not very nice for actual use. I wanted something more convenient and user-friendly.

### The loop solution

Kedro nodes are just Python functions. There's nothing stopping you from putting a loop inside a node:

```python
def query_llm_cli(
    transcript_chunks: Dict[str, Any] = None,
    wiki_embeddings: Dict[str, Dict[str, Any]] = None,
    character_list: List[str] = None,
    # ... other parameters ...
) -> None:
    """Interactive conversation loop for CLI chatbot."""
    api_key = get_openai_api_key()
    llm = get_llm(api_key=api_key, model=llm_model_name, temperature=llm_temperature)
    conversation_history: List[Any] = []

    while True:
        user_query = input("🟢 You: ").strip()
        if user_query.lower() in {"exit", "quit"}:
            break

        # Find relevant contexts and format prompt
        contexts = find_relevant_contexts(query=user_query, ...)
        new_messages = format_prompt_with_context(...)
        
        conversation_history.extend(new_messages)
        response = llm.invoke(conversation_history)
        
        print(f"\n⚪ LLM: {response.content}\n")
        conversation_history.append({"role": "ai", "content": response.content})
```

This approach leverages LangChain's `ChatPromptTemplate` (loaded via our `LangChainPromptDataset`) to maintain conversation history. The chatbot now has memory of previous exchanges, making the interaction feel natural and conversational.

## Games belong on Discord

As a stretch goal, I wanted to make this a Discord bot. It seemed fitting. A gaming knowledge base should live where people game. It also brought some interesting insights from an architecture perspective.

### The async challenge

To get my Kedro runs to interact with Discord, I used Discord.py, an open-source Python API wrapper for Discord.

Discord.py is built on asyncio. Kedro pipeline runs are blocking operations. These two paradigms don't play well together.

**Solution: bootstrap and thread**

Each Discord command bootstraps its own Kedro session and runs the pipeline in a separate thread:

```python
def setup_kedro_project() -> Path:
    """Bootstrap and configure Kedro project."""
    project_path = Path(__file__).resolve().parent
    metadata = bootstrap_project(project_path)
    configure_project(metadata.package_name)
    return project_path

@bot.command(name="/query")
async def run_query(ctx: commands.Context, *, user_query: str) -> None:
    """Run Kedro query pipeline asynchronously."""
    await ctx.send(f"🚀 Running Kedro pipeline for query: `{user_query}`...")
    
    project_path = setup_kedro_project()
    
    def run_kedro() -> Any:
        with KedroSession.create(
            project_path=project_path,
            runtime_params={"user_query": user_query}
        ) as session:
            return session.run(pipeline_name="query_pipeline", tags=["discord"])
    
    result = await asyncio.to_thread(run_kedro)
    # ... process and send response ...
```

This approach has a nice side effect: each query runs in its own pipeline execution, so multiple users can query the bot simultaneously without interfering with each other.

### The message length problem

Discord has a 2000-character limit per message. LLM responses can easily exceed this. The solution was a simple chunking function:

```python
DISCORD_MAX_MESSAGE_LENGTH = 2000
DISCORD_SAFE_MESSAGE_LENGTH = 1900

async def send_long_message(ctx: commands.Context, message: str) -> None:
    """Send message to Discord, chunking if it exceeds 2000 characters."""
    if len(message) <= DISCORD_SAFE_MESSAGE_LENGTH:
        await ctx.send(message)
    else:
        for i in range(0, len(message), DISCORD_MAX_MESSAGE_LENGTH):
            await ctx.send(message[i:i+DISCORD_MAX_MESSAGE_LENGTH])
```

### The pipeline architecture challenge

Here's where I got some interesting insights about Kedro pipeline design. The Discord bot and CLI chatbot needed different behaviors:

* **CLI**: Interactive loop, maintains conversation history
* **Discord**: Single query, no history, returns string response

**Attempt 1: duplicate pipelines**

My first instinct was to create separate pipelines. This worked but violated DRY principles and Kedro best practices. Not ideal. In fact, Kedro does not even allow nodes to have the same name even if they're in different pipelines. The framework that exists to apply proper software development practices to data projects was doing its job.

**Attempt 2: separate pipelines with tags**

I tried splitting into three pipelines:

1. Context retrieval and prompt assembly (shared)
2. CLI LLM query node
3. Discord LLM query node

The idea was to use tags to control execution. This failed because I couldn't guarantee execution order—sometimes the LLM node would run before context retrieval, leading to hallucinations from empty context.

**Solution: single pipeline with tagged nodes**

The chosen approach was a single pipeline with all nodes, using tags to select execution paths:

```python
def create_pipeline() -> Pipeline:
    return Pipeline([
        Node(
            func=find_relevant_contexts,
            inputs=[...],
            outputs="relevant_contexts",
            tags=["cli", "discord"],  # Shared node
        ),
        Node(
            func=format_prompt_with_context,
            inputs=[...],
            outputs="formatted_prompt",
            tags=["cli", "discord"],  # Shared node
        ),
        Node(
            func=query_llm_cli,
            inputs=[...],
            outputs="llm_response_cli",
            tags=["cli"],  # CLI-only
        ),
        Node(
            func=query_llm_discord,
            inputs=[...],
            outputs="llm_response_discord",
            tags=["discord"],  # Discord-only
        ),
    ])
```

Now I can run:

* `kedro run --pipeline=query_pipeline --tags=cli` for CLI mode
* `kedro run --pipeline=query_pipeline --tags=discord` for Discord mode

Kedro's tag system ensures only the appropriate nodes run, and execution order is guaranteed because nodes are connected by their inputs and outputs. This is the Kedro way: use the framework's features to solve problems elegantly.

## Lessons learned

This project started with building a simple query system to test a new dataset. It ended up being a very insightful learning experience.

### 1. Separation of concerns is important

Having separate pipelines for processing and querying meant I could iterate on query logic without reprocessing 400 pages of transcript and 13,000 wiki pages. This separation, enforced by Kedro's architecture, was a great time saver.

### 2. The data catalog is your friend

Never hardcode file paths. The catalog makes it trivial to:

* Change data locations
* Use different datasets for testing vs. production
* Track data lineage

### 3. Parameters enable experimentation

Moving magic numbers to `parameters.yml` made it easy to experiment:

* What's the optimal chunk size?
* How much overlap is needed?
* What temperature works best for this use case?

Change a parameter, rerun the pipeline. No code changes needed.

### 4. Nodes are just functions

Don't overthink it. A node can be a simple transformation, a complex loop, or anything in between. Kedro provides structure, not restrictions.

### 5. Tags are powerful

The tag system solved a real architectural problem elegantly. It's a simple feature with powerful implications for pipeline organization.

## Conclusion: from experiment to production pattern

What started as a test of an experimental dataset became a comprehensive exploration of building production-ready data pipelines with Kedro. The project demonstrates:

* **RAG system architecture** using semantic search
* **Custom dataset integration** with LangChain
* **Pipeline organization** for different execution modes
* **Async integration** with blocking operations
* **Practical constraints** and trade-offs in real systems

The code is clean, maintainable, and follows Kedro best practices. More importantly, it works. The bot can answer questions about Cyberpunk 2077, drawing from both the game transcript and comprehensive wiki data.

And after 466 hours of gameplay and every achievement unlocked, I can confirm: the bot's answers are accurate. Now if only it could tell me when the sequel's release date is going to be.

## Resources

* [Kedro documentation](https://docs.kedro.org/) - Comprehensive guide to Kedro
* [LangChain documentation](https://python.langchain.com/) - LLM framework
* [Discord.py documentation](https://discordpy.readthedocs.io/) - Discord bot library
* [Sentence Transformers](https://www.sbert.net/) - Semantic embeddings
* [OpenAI API](https://platform.openai.com/docs) - LLM provider
* [Cyberpunk Wiki](https://cyberpunk.fandom.com/wiki/Cyberpunk_Wiki) - Game information source
* [Full Cyberpunk 2077 transcript](https://game-scripts-wiki.blogspot.com/2020/12/cyberpunk-2077-full-transcript.html) - Transcript source

---

*The complete project is available on GitHub as part of the Kedro Academy repository. Feel free to explore, experiment, and adapt it for your own use cases.*


