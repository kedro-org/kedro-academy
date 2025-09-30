import json
import hashlib
from pathlib import Path
from typing import Any, Literal, Union, TYPE_CHECKING

from kedro.io import AbstractDataset

if TYPE_CHECKING:
    from kedro_datasets.json import JSONDataset
    from kedro_datasets.yaml import YAMLDataset
from langchain.prompts import ChatPromptTemplate
from langfuse import Langfuse


def _hash(data: str | list) -> str:
    """Return SHA-256 hash of a prompt (string or list of messages)."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _get_content(data: str | list) -> str:
    """
    Extract comparable text content from a prompt.
    - If string: return as-is.
    - If list of messages: join their `content`.
    """
    if isinstance(data, str):
        return data
    return "\n".join(msg["content"] for msg in data)


class LangfusePromptDataset(AbstractDataset):
    """
    Kedro dataset for managing prompts with Langfuse versioning.

    Behavior:
    - On save: writes prompt JSON to disk and creates/updates it in Langfuse.
    - On load: syncs based on sync_policy, ensures reproducibility.
    - Returns LangChain `ChatPromptTemplate` (langchain mode) or raw Langfuse object (sdk mode).

    Sync policies:
    - local: local file takes precedence (default)
    - remote: Langfuse version takes precedence (errors if remote doesn't exist)
    - strict: error if local and remote differ
    
    Version/Label support (via load_args):
    - Default (no load_args): Uses latest version (handles first-time loading gracefully)
    - load_args: {version: 3}: Load specific version number
    - load_args: {label: "staging"}: Load version pointed to by label  
    - Cannot specify both version and label (Langfuse will raise ValueError)
    
    Save configuration (via save_args):
    - save_args: {labels: ["staging", "v2.1"]}: Assign labels to new versions
    """

    def __init__(
        self,
        filepath: str,
        prompt_name: str,
        credentials: dict[str, Any],
        prompt_type: Literal["chat", "text"] = "text",
        sync_policy: Literal["local", "remote", "strict"] = "local",
        mode: Literal["langchain", "sdk"] = "langchain",
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize LangfusePromptDataset for managing prompts with Langfuse versioning.
        
        This dataset provides seamless integration between local prompt files (JSON/YAML) 
        and Langfuse prompt management, supporting version control, labeling, and 
        different synchronization policies.
        
        Args:
            filepath: Local file path for storing prompt. Supports .json, .yaml, .yml extensions.
            prompt_name: Unique identifier for the prompt in Langfuse.
            prompt_type: Type of prompt - "chat" for conversation or "text" for single prompts.
            credentials: Dict with Langfuse credentials {public_key, secret_key, host}.
            sync_policy: How to handle conflicts between local and remote:
                - "local": Local file takes precedence (default)
                - "remote": Langfuse version takes precedence 
                - "strict": Error if local and remote differ
            mode: Return type for load() method:
                - "langchain": Returns ChatPromptTemplate object (default)
                - "sdk": Returns raw Langfuse prompt object
            load_args: Dict with loading parameters. Supported keys:
                - version (int): Specific version number to load
                - label (str): Specific label to load (e.g., "production", "staging")
                Note: Cannot specify both version and label simultaneously.
            save_args: Dict with saving parameters. Supported keys:
                - labels (list[str]): List of labels to assign to new prompt versions
        
        Examples:
            >>> # Basic usage with default settings
            >>> dataset = LangfusePromptDataset(
            ...     filepath="prompts/intent.json",
            ...     prompt_name="intent-classifier",
            ...     credentials={"public_key": "pk_...", "secret_key": "sk_...", "host": "..."}
            ... )
            
            >>> # Load specific version with remote-first policy
            >>> dataset = LangfusePromptDataset(
            ...     filepath="prompts/intent.yaml",
            ...     prompt_name="intent-classifier", 
            ...     credentials=creds,
            ...     sync_policy="remote",
            ...     load_args={"version": 3}
            ... )
            
            >>> # Auto-label new versions when saving
            >>> dataset = LangfusePromptDataset(
            ...     filepath="prompts/intent.json",
            ...     prompt_name="intent-classifier",
            ...     credentials=creds,
            ...     save_args={"labels": ["staging", "v2.1"]}
            ... )
        
        Raises:
            ValueError: If credentials are missing required keys.
            NotImplementedError: If filepath has unsupported extension.
        """
        self._filepath = Path(filepath)
        self._prompt_name = prompt_name
        self._prompt_type: Literal["chat", "text"] = prompt_type
        self._langfuse = Langfuse(
            public_key=credentials["public_key"],
            secret_key=credentials["secret_key"],
            host=credentials["host"],
        )
        self._sync_policy = sync_policy
        self._mode = mode
        self._load_args = load_args or {}
        self._save_args = save_args or {}
        self._file_dataset = None

    def _describe(self) -> dict[str, Any]:
        """
        Return a description of the dataset for Kedro's internal use.
        
        This method is called by Kedro's catalog system to get metadata about
        the dataset for logging and debugging purposes.
        
        Returns:
            dict: Dictionary containing dataset description with keys:
                - filepath: Path to the local prompt file
                - prompt_name: Name of the prompt in Langfuse
                
        Examples:
            >>> dataset._describe()
            {'filepath': PosixPath('prompts/intent.json'), 'prompt_name': 'intent-classifier'}
        """
        return {"filepath": self._filepath, "prompt_name": self._prompt_name}

    @property
    def file_dataset(self) -> Union["JSONDataset", "YAMLDataset"]:
        """
        Get appropriate Kedro dataset based on file extension (cached).
        
        Dynamically imports and returns the correct dataset type based on the file
        extension of the configured filepath. Uses lazy imports to avoid unnecessary
        dependencies while maintaining proper type checking through TYPE_CHECKING imports.
        
        The dataset instance is cached after first access for performance optimization.
        
        Returns:
            JSONDataset: For .json files
            YAMLDataset: For .yaml/.yml files
            
        Raises:
            NotImplementedError: If file extension is not supported
            
        Examples:
            >>> # For a dataset with filepath="prompts/intent.json"
            >>> dataset = self.file_dataset
            >>> type(dataset).__name__
            'JSONDataset'
            
            >>> # For a dataset with filepath="prompts/intent.yaml" 
            >>> dataset = self.file_dataset
            >>> type(dataset).__name__
            'YAMLDataset'
        """
        if self._file_dataset is None:
            if self._filepath.suffix.lower() in ['.yaml', '.yml']:
                from kedro_datasets.yaml import YAMLDataset
                self._file_dataset = YAMLDataset(filepath=str(self._filepath))
            elif self._filepath.suffix.lower() in ['.json']:
                from kedro_datasets.json import JSONDataset
                self._file_dataset = JSONDataset(filepath=str(self._filepath))
            else:
                raise NotImplementedError(
                    f"Unsupported file extension '{self._filepath.suffix}'. "
                    f"Supported formats: .json, .yaml, .yml"
                )
        return self._file_dataset

    def save(self, data: str) -> None:
        """
        Save prompt data to local file and create new version in Langfuse.
        
        This method performs a two-step save operation:
        1. Saves the prompt data to the local file using appropriate format (JSON/YAML)
        2. Creates a new prompt version in Langfuse with optional labeling
        
        The save operation respects the save_args configuration for automatic labeling
        of new prompt versions.
        
        Args:
            data: The prompt content to save. Can be string or structured data
                 depending on the prompt type and file format.
                 
        Raises:
            NotImplementedError: If file extension is not supported
            LangfuseError: If Langfuse API call fails
            FileNotFoundError: If parent directory cannot be created
            
        Examples:
            >>> # Save a simple text prompt
            >>> dataset.save("You are a helpful assistant.")
            
            >>> # Save a chat prompt (list of messages)
            >>> chat_prompt = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "{{user_input}}"}
            ... ]
            >>> dataset.save(chat_prompt)
            
            >>> # With auto-labeling (if save_args contains labels)
            >>> # This will create a new version and assign specified labels
            >>> dataset_with_labels = LangfusePromptDataset(
            ...     filepath="prompts/intent.json",
            ...     prompt_name="intent-classifier",
            ...     credentials=creds,
            ...     save_args={"labels": ["staging", "v2.1"]}
            ... )
            >>> dataset_with_labels.save("New prompt content")
            # Creates version and assigns "staging" and "v2.1" labels
        """
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        self.file_dataset.save(data)

        create_kwargs = {
            "name": self._prompt_name,
            "prompt": data,
            "type": self._prompt_type,
        }
        
        # Add labels from save_args if specified
        if "labels" in self._save_args:
            create_kwargs["labels"] = self._save_args["labels"]
            
        self._langfuse.create_prompt(**create_kwargs)

    def _build_get_kwargs(self) -> dict[str, Any]:
        """
        Build kwargs for fetching prompt from Langfuse based on load_args.
        
        Respects user's specified version/label from load_args configuration.
        Defaults to "latest" label if no specific version or label is specified.
        
        Returns:
            dict: Kwargs dictionary for langfuse.get_prompt() with keys:
                - name: The prompt name
                - type: The prompt type
                - version (int, optional): Specific version number if specified
                - label (str, optional): Specific label if specified, defaults to "latest"
        """
        get_kwargs = {"name": self._prompt_name, "type": self._prompt_type}
        if self._load_args.get("label") is not None:
            get_kwargs["label"] = self._load_args["label"]
        elif self._load_args.get("version") is not None:
            get_kwargs["version"] = self._load_args["version"]
        else:
            get_kwargs["label"] = "latest"
        return get_kwargs

    def _sync_strict_policy(
        self, local_data: str | None, langfuse_prompt: Any | None
    ) -> Any:
        """
        Handle strict sync policy - error if local and remote differ or either is missing.
        
        Args:
            local_data: Content from local file, None if file doesn't exist
            langfuse_prompt: Langfuse prompt object, None if not found remotely
            
        Returns:
            Any: Langfuse prompt object if sync is successful
            
        Raises:
            ValueError: If either local_data or langfuse_prompt is missing, or if they differ
        """
        if not local_data or not langfuse_prompt:
            raise ValueError(
                f"Strict sync policy specified for '{self._prompt_name}' "
                f"but no local_data or remote prompt exists in Langfuse."
            )

        local_hash = _hash(_get_content(local_data))
        remote_hash = _hash(_get_content(langfuse_prompt.prompt))
        if local_hash != remote_hash:
            raise ValueError(
                f"Strict sync failed for '{self._prompt_name}': "
                f"local and remote prompts differ. Use 'local' or 'remote' policy to resolve."
            )
        return langfuse_prompt

    def _normalize_message_types(self, prompt_data):
        # TODO: When langfuse returns prompt response, it sends the type as message
        # Not sure how else to fix this
        """Convert 'message' type to 'chatmessage' for chat prompts."""
        if self._prompt_type == "chat" and isinstance(prompt_data, list):
            for msg in prompt_data:
                if isinstance(msg, dict) and msg.get("type") == "message":
                    msg["type"] = "chatmessage"
        return prompt_data

    def _sync_remote_policy(
        self, local_data: str | None, langfuse_prompt: Any | None
    ) -> Any:
        """
        Handle remote sync policy - Langfuse version takes precedence.
        
        Args:
            local_data: Content from local file, None if file doesn't exist
            langfuse_prompt: Langfuse prompt object, None if not found remotely
            
        Returns:
            Any: Langfuse prompt object after updating local file if needed
            
        Raises:
            ValueError: If remote prompt doesn't exist
        """
        if not langfuse_prompt:
            raise ValueError(
                f"Remote sync policy specified for '{self._prompt_name}' "
                f"but no remote prompt exists in Langfuse. Create the prompt in Langfuse first."
            )
        if not local_data or _hash(_get_content(local_data)) != _hash(_get_content(langfuse_prompt.prompt)):
            self._filepath.parent.mkdir(parents=True, exist_ok=True)
            normalized_prompt = self._normalize_message_types(langfuse_prompt.prompt)
            self.file_dataset.save(normalized_prompt)
        return langfuse_prompt

    def _sync_local_policy(
        self, local_data: str | None, langfuse_prompt: Any | None
    ) -> Any:
        """
        Handle local sync policy - local file takes precedence.
        
        Args:
            local_data: Content from local file, None if file doesn't exist
            langfuse_prompt: Langfuse prompt object, None if not found remotely
            
        Returns:
            Any: Langfuse prompt object after syncing
            
        Raises:
            FileNotFoundError: If neither local nor remote prompt exists
        """
        if local_data is not None:
            if langfuse_prompt is None:
                # Push local to Langfuse
                self.save(local_data)
                return self._langfuse.get_prompt(**self._build_get_kwargs())

            # If mismatch → update Langfuse with local
            if _hash(_get_content(local_data)) != _hash(
                _get_content(langfuse_prompt.prompt)
            ):
                self.save(local_data)
                return self._langfuse.get_prompt(**self._build_get_kwargs())
            return langfuse_prompt

        # If local missing but Langfuse exists → persist locally
        if langfuse_prompt:
            self._filepath.parent.mkdir(parents=True, exist_ok=True)
            normalized_prompt = self._normalize_message_types(langfuse_prompt.prompt)
            self.file_dataset.save(normalized_prompt)
            return langfuse_prompt

        raise FileNotFoundError(
            f"No prompt found locally or in Langfuse for '{self._prompt_name}'"
        )

    def _sync_with_langfuse(
        self, local_data: str | None, langfuse_prompt: Any | None
    ) -> Any:
        """
        Synchronize local file and Langfuse prompt based on configured sync policy.
        
        This method delegates to specialized sync policy handlers based on the
        configured sync_policy setting.
        
        Args:
            local_data: Content from local file, None if file doesn't exist
            langfuse_prompt: Langfuse prompt object, None if not found remotely
            
        Returns:
            Any: Langfuse prompt object after synchronization
            
        Raises:
            ValueError: Based on sync_policy conflicts (see individual policy methods)
            FileNotFoundError: If no prompt found locally or in Langfuse
        """
        if self._sync_policy == "strict":
            return self._sync_strict_policy(local_data, langfuse_prompt)
        elif self._sync_policy == "remote":
            return self._sync_remote_policy(local_data, langfuse_prompt)
        else:  # local policy (default)
            return self._sync_local_policy(local_data, langfuse_prompt)

    def load(self) -> ChatPromptTemplate | Any:
        """
        Load prompt from Langfuse with local file synchronization.
        
        This method performs the complete load workflow:
        1. Loads local file if it exists
        2. Attempts to fetch prompt from Langfuse using configured version/label (if specified)
        3. Synchronizes local and remote versions based on sync_policy
        4. Returns prompt in the format specified by mode parameter
        
        The method respects load_args for version/label specification and handles
        various sync scenarios automatically, including first-time loading scenarios.
        
        Returns:
            ChatPromptTemplate: If mode="langchain" (default)
                Ready-to-use LangChain prompt template with variable substitution
            Any: If mode="sdk"
                Raw Langfuse prompt object with full API access
                
        Raises:
            ValueError: Based on sync_policy conflicts (see _sync_with_langfuse)
            FileNotFoundError: If no prompt found locally or in Langfuse
            NotImplementedError: If file extension is not supported
            LangfuseError: If Langfuse API calls fail
            
        Examples:
            >>> # Load with default settings (latest version, langchain mode)
            >>> prompt_template = dataset.load()
            >>> formatted = prompt_template.format(user_input="Hello world")
            
            >>> # Load specific version in SDK mode
            >>> dataset_v3 = LangfusePromptDataset(
            ...     filepath="prompts/intent.json",
            ...     prompt_name="intent-classifier",
            ...     credentials=creds,
            ...     mode="sdk",
            ...     load_args={"version": 3}
            ... )
            >>> langfuse_prompt = dataset_v3.load()
            >>> print(f"Version: {langfuse_prompt.version}")
            >>> print(f"Labels: {langfuse_prompt.labels}")
            
            >>> # Load from staging environment
            >>> staging_dataset = LangfusePromptDataset(
            ...     filepath="prompts/staging.yaml",
            ...     prompt_name="intent-classifier",
            ...     credentials=creds,
            ...     sync_policy="remote",
            ...     load_args={"label": "staging"}
            ... )
            >>> prompt = staging_dataset.load()
            
            >>> # Handle different prompt types
            >>> if dataset._prompt_type == "chat":
            ...     # Chat prompts return templates with message formatting
            ...     messages = prompt.format_messages(user_input="test")
            ... else:
            ...     # Text prompts return simple string templates
            ...     text = prompt.format(user_input="test")
        """
        try:
            if self._load_args.get("label") is not None:
                langfuse_prompt = self._langfuse.get_prompt(
                    self._prompt_name, 
                    type=self._prompt_type,
                    label=self._load_args.get("label")
                )
            elif self._load_args.get("version") is not None:
                  langfuse_prompt = self._langfuse.get_prompt(
                    self._prompt_name, 
                    type=self._prompt_type, 
                    version=self._load_args.get("version")
                )
            else:
                # Try to fetch latest
                langfuse_prompt = self._langfuse.get_prompt(
                    self._prompt_name, 
                    type=self._prompt_type,
                    label="latest"
                )
        except Exception:
            langfuse_prompt = None

        # Load local file if it exists
        local_data = None
        if self._filepath.exists():
            local_data = self.file_dataset.load()

        # Synchronize local and remote
        langfuse_prompt = self._sync_with_langfuse(local_data, langfuse_prompt)

        if self._mode == "sdk":
            return langfuse_prompt
        else:
            return ChatPromptTemplate.from_messages(langfuse_prompt.get_langchain_prompt())
