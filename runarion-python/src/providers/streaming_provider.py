import time
import uuid
from typing import Generator, Dict, Any, Optional, Type
from abc import ABC, abstractmethod
from flask import current_app

from models.request import BaseGenerationRequest
from providers.base_provider import BaseProvider

class StreamingProvider(BaseProvider, ABC):
    """
    Base class for streaming providers.
    
    This extends the BaseProvider with streaming capabilities.
    """
    
    @abstractmethod
    def stream(self) -> Generator[str, None, None]:
        """
        Stream text generation from the provider.
        
        Yields:
            str: Text chunks as they are generated.
        """
        pass

class OpenAIStreamingProvider(StreamingProvider):
    """
    OpenAI streaming provider implementation.
    """
    
    def __init__(self, request: BaseGenerationRequest):
        super().__init__(request)
        
        # Ensure we're using the OpenAI client
        import openai
        from openai import OpenAI
        
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def stream(self) -> Generator[str, None, None]:
        """
        Stream text generation from OpenAI.
        
        Yields:
            str: Text chunks as they are generated.
        """
        try:
            # Build OpenAI kwargs
            openai_kwargs = self._build_openai_kwargs(self.request.generation_config)
            
            # Ensure streaming is enabled
            openai_kwargs["stream"] = True
            
            # Log the request
            current_app.logger.info(f"OpenAI streaming request: {openai_kwargs}")
            
            # Make the streaming request
            stream = self.client.chat.completions.create(**openai_kwargs)
            
            # Process the stream
            for chunk in stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                        content = choice.delta.content
                        if content:
                            yield content
            
        except Exception as e:
            current_app.logger.error(f"OpenAI streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def _build_openai_kwargs(self, config) -> Dict[str, Any]:
        """
        Build kwargs for OpenAI API.
        
        Args:
            config: Generation configuration.
            
        Returns:
            Dict[str, Any]: OpenAI API kwargs.
        """
        messages = []
        if self.instruction:
            messages.append({"role": "system", "content": self.instruction})
        if self.request.prompt:
            messages.append({"role": "user", "content": self.request.prompt})
            
        logit_bias = {}    
        if config.banned_tokens:
            for token_id in config.banned_tokens:
                logit_bias[str(token_id)] = -100
        
        if config.phrase_bias:
            for item in config.phrase_bias:
                for token_id_str, bias_value in item.items():
                    # Ensure token_id_str is a string
                    logit_bias[token_id_str] = bias_value
                
        openai_kwargs = {
            "messages": messages,
            "model" : self.model,
            "frequency_penalty": config.repetition_penalty,
            "presence_penalty": config.repetition_penalty,
            "stop": config.stop_sequences if config.stop_sequences else None,
            "temperature": config.temperature,
            "top_p": config.nucleus_sampling,
            "logit_bias": logit_bias if logit_bias else None,
            "max_tokens": config.max_output_tokens, 
            "stream": True  # Always stream
        }
        
        return {k: v for k, v in openai_kwargs.items() if v is not None}
    
    def generate(self):
        """
        Non-streaming generation is not supported by this provider.
        """
        raise NotImplementedError("This provider only supports streaming. Use stream() instead.")

class GeminiStreamingProvider(StreamingProvider):
    """
    Gemini streaming provider implementation.
    """
    
    def __init__(self, request: BaseGenerationRequest):
        super().__init__(request)
        
        # Ensure we're using the Google Generative AI client
        import google.generativeai as genai
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")
    
    def stream(self) -> Generator[str, None, None]:
        """
        Stream text generation from Gemini.
        
        Yields:
            str: Text chunks as they are generated.
        """
        try:
            # Build Gemini generation config
            generation_config = self._build_gemini_config(self.request.generation_config)
            
            # Create the model
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Prepare the prompt
            prompt_parts = []
            if self.instruction:
                prompt_parts.append(self.instruction)
            if self.request.prompt:
                prompt_parts.append(self.request.prompt)
            
            # Log the request
            current_app.logger.info(f"Gemini streaming request: {prompt_parts}")
            
            # Make the streaming request
            response = model.generate_content(
                prompt_parts,
                stream=True
            )
            
            # Process the stream
            for chunk in response:
                if hasattr(chunk, 'text'):
                    if chunk.text:
                        yield chunk.text
            
        except Exception as e:
            current_app.logger.error(f"Gemini streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def _build_gemini_config(self, config) -> Dict[str, Any]:
        """
        Build generation config for Gemini API.
        
        Args:
            config: Generation configuration.
            
        Returns:
            Dict[str, Any]: Gemini generation config.
        """
        gemini_config = {
            "temperature": config.temperature,
            "top_p": config.nucleus_sampling,
            "top_k": int(config.top_k * 40) if config.top_k > 0 else None,
            "max_output_tokens": config.max_output_tokens,
        }
        
        # Add stop sequences if provided
        if config.stop_sequences:
            gemini_config["stop_sequences"] = config.stop_sequences
        
        return {k: v for k, v in gemini_config.items() if v is not None}
    
    def generate(self):
        """
        Non-streaming generation is not supported by this provider.
        """
        raise NotImplementedError("This provider only supports streaming. Use stream() instead.")

class StreamingProviderFactory:
    """
    Factory for creating streaming providers.
    """
    
    _provider_registry = {
        "openai": OpenAIStreamingProvider,
        "gemini": GeminiStreamingProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[StreamingProvider]):
        """
        Register a new streaming provider.
        
        Args:
            name: Provider name.
            provider_cls: Provider class.
        """
        cls._provider_registry[name.lower()] = provider_cls
    
    @classmethod
    def create_provider(cls, provider_name: str, request: BaseGenerationRequest) -> StreamingProvider:
        """
        Create a streaming provider instance.
        
        Args:
            provider_name: Provider name.
            request: Generation request.
            
        Returns:
            StreamingProvider: Provider instance.
            
        Raises:
            ValueError: If the provider is not supported.
        """
        try:
            provider_cls = cls._provider_registry.get(provider_name.lower())
            if not provider_cls:
                raise ValueError(f"Unsupported provider: {provider_name}")
            
            return provider_cls(request)
        except Exception as e:
            current_app.logger.error(f"Failed to create streaming provider: {e}")
            raise
