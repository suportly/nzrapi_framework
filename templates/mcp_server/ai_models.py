"""
AI model implementations for {{ project_name }}
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

from nzrrest.ai.models import AIModel


class CustomChatModel(AIModel):
    """Custom chat model implementation for conversational AI"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.conversation_memory = {}
        self.system_prompt = config.get(
            "system_prompt",
            "You are a helpful AI assistant built with nzrRest framework.",
        )
        self.max_context_length = config.get("max_context_length", 10)

    async def load_model(self) -> None:
        """Load the chat model"""
        # Simulate model loading
        await asyncio.sleep(0.1)
        self.is_loaded = True
        print(f"✅ Loaded custom chat model: {self.name}")

    async def predict(
        self, payload: Dict[str, Any], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate chat response with conversation context"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        # Extract input
        user_message = payload.get("message", payload.get("prompt", ""))
        context_id = payload.get("context_id", "default")

        # Manage conversation context
        if context_id not in self.conversation_memory:
            self.conversation_memory[context_id] = [
                {"role": "system", "content": self.system_prompt}
            ]

        # Add user message to context
        conversation = self.conversation_memory[context_id]
        conversation.append({"role": "user", "content": user_message})

        # Trim context if too long
        if len(conversation) > self.max_context_length:
            # Keep system message and recent messages
            conversation = [conversation[0]] + conversation[
                -(self.max_context_length - 1) :
            ]
            self.conversation_memory[context_id] = conversation

        # Generate response (this would call your actual AI model)
        response_text = await self._generate_response(user_message, conversation)

        # Add assistant response to context
        conversation.append({"role": "assistant", "content": response_text})

        return {
            "response": response_text,
            "context_id": context_id,
            "conversation_length": len(conversation),
            "model": self.name,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _generate_response(self, message: str, conversation: list) -> str:
        """Generate AI response (implement your AI logic here)"""
        # This is a placeholder - implement your actual AI model logic here

        # Simple rule-based responses for demonstration
        message_lower = message.lower()

        if "hello" in message_lower or "hi" in message_lower:
            return f"Hello! I'm {self.name}, ready to help you."

        elif "how are you" in message_lower:
            return "I'm functioning well! How can I assist you today?"

        elif "weather" in message_lower:
            return "I don't have access to real-time weather data, but I can help you with other questions!"

        elif "capabilities" in message_lower or "what can you do" in message_lower:
            return """I can help you with:
            - Answering questions
            - Having conversations
            - Providing information
            - Helping with various tasks
            
            I'm built with the nzrRest framework for AI APIs!"""

        else:
            return f"I understand you said: '{message}'. How can I help you with that?"

    async def unload_model(self) -> None:
        """Unload the chat model"""
        self.conversation_memory.clear()
        self.is_loaded = False
        print(f"❌ Unloaded custom chat model: {self.name}")

    @property
    def model_info(self) -> Dict[str, str]:
        """Get model information"""
        return {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "type": "custom_chat",
            "description": "Custom conversational AI model",
            "capabilities": "chat,conversation,context_aware",
            "max_context_length": str(self.max_context_length),
        }


class TextAnalysisModel(AIModel):
    """Model for text analysis tasks"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.analysis_types = config.get(
            "analysis_types", ["sentiment", "keywords", "summary", "entities"]
        )

    async def load_model(self) -> None:
        """Load the text analysis model"""
        await asyncio.sleep(0.1)
        self.is_loaded = True
        print(f"✅ Loaded text analysis model: {self.name}")

    async def predict(
        self, payload: Dict[str, Any], context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze text and return structured results"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        text = payload.get("text", "")
        analysis_type = payload.get("analysis_type", "all")

        if not text:
            raise ValueError("Text is required for analysis")

        results = {}

        # Perform different types of analysis
        if analysis_type == "all" or "sentiment" in analysis_type:
            results["sentiment"] = self._analyze_sentiment(text)

        if analysis_type == "all" or "keywords" in analysis_type:
            results["keywords"] = self._extract_keywords(text)

        if analysis_type == "all" or "summary" in analysis_type:
            results["summary"] = self._generate_summary(text)

        if analysis_type == "all" or "entities" in analysis_type:
            results["entities"] = self._extract_entities(text)

        return {
            "analysis_results": results,
            "text_length": len(text),
            "analysis_type": analysis_type,
            "model": self.name,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        # Simple rule-based sentiment analysis (replace with actual model)
        positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
        ]
        negative_words = ["bad", "terrible", "awful", "horrible", "disappointing"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            sentiment = "positive"
            score = min(0.5 + (positive_count * 0.2), 1.0)
        elif negative_count > positive_count:
            sentiment = "negative"
            score = max(0.5 - (negative_count * 0.2), 0.0)
        else:
            sentiment = "neutral"
            score = 0.5

        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "confidence": 0.8,  # Placeholder confidence
        }

    def _extract_keywords(self, text: str) -> list:
        """Extract keywords from text"""
        # Simple keyword extraction (replace with actual NLP)
        import re

        # Remove punctuation and split into words
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }

        # Count word frequency
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]

    def _generate_summary(self, text: str) -> str:
        """Generate summary of text"""
        # Simple extractive summary (replace with actual model)
        sentences = text.split(".")
        if len(sentences) <= 2:
            return text

        # Return first and last sentences as summary
        summary = sentences[0].strip() + ". " + sentences[-1].strip() + "."
        return summary

    def _extract_entities(self, text: str) -> list:
        """Extract named entities from text"""
        # Simple entity extraction (replace with actual NER model)
        import re

        entities = []

        # Extract email addresses
        emails = re.findall(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text
        )
        for email in emails:
            entities.append({"text": email, "type": "EMAIL"})

        # Extract URLs
        urls = re.findall(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            text,
        )
        for url in urls:
            entities.append({"text": url, "type": "URL"})

        # Extract capitalized words (potential proper nouns)
        proper_nouns = re.findall(r"\b[A-Z][a-z]+\b", text)
        for noun in proper_nouns:
            if len(noun) > 2:
                entities.append({"text": noun, "type": "PERSON_OR_PLACE"})

        return entities

    async def unload_model(self) -> None:
        """Unload the text analysis model"""
        self.is_loaded = False
        print(f"❌ Unloaded text analysis model: {self.name}")

    @property
    def model_info(self) -> Dict[str, str]:
        """Get model information"""
        return {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "type": "text_analysis",
            "description": "Text analysis model for sentiment, keywords, and entities",
            "capabilities": "sentiment_analysis,keyword_extraction,summarization,entity_extraction",
            "supported_analysis": ",".join(self.analysis_types),
        }
