# ai_edit/core/ai_client.py
"""
Client for interacting with the Azure OpenAI service.
"""

from typing import Any, Dict, List

import click  # Import click for colored output
from openai import APIError, AzureOpenAI


class AIClient:
    """Handles communication with the Azure OpenAI API."""

    def __init__(self, config: Dict[str, Any], debug: bool = False):
        """
        Initializes the AI client with Azure credentials.

        Args:
            config: A dictionary containing Azure configuration.
            debug: Whether to print debug messages.
        """
        if not all(k in config for k in ["endpoint", "api_key", "api_version", "model"]):
            raise ValueError("Azure configuration is missing required keys.")

        self.client = AzureOpenAI(
            azure_endpoint=config["endpoint"],
            api_key=config["api_key"],
            api_version=config["api_version"],
        )
        self.model = config["model"]
        self.config = config
        self.debug = debug

    def get_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Gets a completion from the Azure OpenAI model.

        Args:
            messages: The list of messages in the conversation history.
        """
        if self.debug:
            # Construct and print the full URL for debugging purposes
            endpoint = self.config["endpoint"].strip("/")
            deployment = self.model
            api_version = self.config["api_version"]
            full_url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            click.echo(f"DEBUG: Requesting URL: {full_url}", err=True)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            if response.choices:
                return response.choices[0].message.content or ""
            else:
                return ""
        except APIError as e:
            raise RuntimeError(f"Azure OpenAI API error: {e}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while contacting the AI: {e}")
