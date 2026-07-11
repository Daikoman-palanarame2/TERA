import os
import re
import sys
from typing import List, Tuple, Dict
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

"""
This module manages configuration parameters and API credentials for TERA.
Includes automatic model discovery and capability tier grouping.
"""

def get_model_capability_key(model_name: str) -> Tuple[int, float]:
    """
    Heuristic to classify model capability tiers and parameter sizes.
    Returns a tuple of (tier_priority, size_indicator) where:
      - tier_priority: 0 (cheap), 1 (medium), 2 (dense)
      - size_indicator: parameter count or fallback approximation
    """
    model_lower = model_name.lower()
    
    tier = 1  # medium default
    size = 13.0
    is_known = False
    
    # Priority Heuristic 1: Parameter size match
    if "8x7b" in model_lower:
        tier = 1
        size = 56.0
        is_known = True
    elif "8x22b" in model_lower:
        tier = 2
        size = 176.0
        is_known = True
    else:
        match_b = re.search(r"(\d+)b", model_lower)
        match_m = re.search(r"(\d+)m", model_lower)
        if match_b:
            val = float(match_b.group(1))
            size = val
            is_known = True
            if val <= 10.0:
                tier = 0
            elif val <= 45.0:
                tier = 1
            else:
                tier = 2
        elif match_m:
            val = float(match_m.group(1))
            size = val / 1000.0
            tier = 0
            is_known = True

    # Priority Heuristic 2: Keyword matching (only if parameter size is not matched)
    if not is_known:
        if any(k in model_lower for k in ["small", "mini", "nano", "lite"]):
            tier = 0
            size = 3.0
            is_known = True
        elif any(k in model_lower for k in ["large", "plus", "max", "ultra", "dbrx", "dense"]):
            tier = 2
            size = 70.0
            is_known = True
            if "dbrx" in model_lower:
                size = 132.0
        elif any(k in model_lower for k in ["medium", "pro", "standard"]):
            tier = 1
            size = 13.0
            is_known = True

    if not is_known:
        print(
            f"Warning: Unknown model name '{model_name}'. Classifying as 'medium' tier.",
            file=sys.stderr
        )

    return (tier, size)


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str | None = Field(
        default=None, 
        validation_alias=AliasChoices("openai_api_key", "OPENAI_API_KEY")
    )
    anthropic_api_key: str | None = Field(
        default=None, 
        validation_alias=AliasChoices("anthropic_api_key", "ANTHROPIC_API_KEY")
    )
    google_api_key: str | None = Field(
        default=None, 
        validation_alias=AliasChoices("google_api_key", "GOOGLE_API_KEY")
    )
    fireworks_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("fireworks_api_key", "FIREWORKS_API_KEY")
    )
    fireworks_base_url: str = Field(
        default="https://api.fireworks.ai/inference/v1",
        validation_alias=AliasChoices("fireworks_base_url", "FIREWORKS_BASE_URL")
    )
    allowed_models_str: str = Field(
        default="",
        validation_alias=AliasChoices("allowed_models_str", "ALLOWED_MODELS")
    )

    # Base Model Lane defaults
    cheap_model_default: str = Field(
        default="accounts/fireworks/models/deepseek-v4-pro", 
        validation_alias=AliasChoices("cheap_model_default", "SMALL_MODEL")
    )
    dense_model_default: str = Field(
        default="accounts/fireworks/models/gpt-oss-120b", 
        validation_alias=AliasChoices("dense_model_default", "LARGE_MODEL")
    )
    
    # Router Parameters
    router_threshold: float = Field(
        default=0.65, 
        validation_alias=AliasChoices("router_threshold", "ROUTER_THRESHOLD")
    )
    min_confidence: float = Field(
        default=0.80, 
        validation_alias=AliasChoices("min_confidence", "MIN_CONFIDENCE")
    )
    entropy_threshold: float = Field(
        default=2.7, 
        validation_alias=AliasChoices("entropy_threshold", "ENTROPY_THRESHOLD")
    )
    max_tokens: int = Field(
        default=512, 
        validation_alias=AliasChoices("max_tokens", "MAX_TOKENS")
    )
    
    @property
    def allowed_models(self) -> List[str]:
        """
        Parses ALLOWED_MODELS from comma-separated string into a list.
        Validates that it is not defined as empty/malformed.
        """
        # Read raw env value directly to enforce validation constraints
        allowed_env = os.environ.get("ALLOWED_MODELS")
        if allowed_env is not None:
            clean_val = allowed_env.strip()
            if not clean_val or re.match(r"^[\s,]*$", clean_val):
                raise ValueError("Configuration error: ALLOWED_MODELS is defined but empty or invalid.")
                
        if not self.allowed_models_str:
            return []
        return [m.strip() for m in self.allowed_models_str.split(",") if m.strip()]

    def get_resolved_models(self) -> Tuple[str, str, str]:
        """
        Determines the cheap and dense models.
        Returns:
            Tuple of (cheap_model, dense_model, selection_method)
        """
        allowed = self.allowed_models
        
        # Check Priority 1: Explicit overrides in environment
        # Check both lower and upper case keys
        has_cheap_override = any(
            os.environ.get(k) is not None 
            for k in ["cheap_model", "SMALL_MODEL", "cheap_model_default"]
        )
        has_dense_override = any(
            os.environ.get(k) is not None 
            for k in ["dense_model", "LARGE_MODEL", "dense_model_default"]
        )
        
        if has_cheap_override or has_dense_override:
            # Fall back to parsed defaults if only one is overridden
            return self.cheap_model_default, self.dense_model_default, "Manual Override"

        # Check Priority 2: Automatic discovery from ALLOWED_MODELS
        if allowed:
            # Sort allowed models using get_model_capability_key
            sorted_models = sorted(allowed, key=get_model_capability_key)
            cheap = sorted_models[0]
            dense = sorted_models[-1]
            return cheap, dense, "Automatic Discovery"

        # Fallback if ALLOWED_MODELS is not defined/empty and no overrides exist
        return self.cheap_model_default, self.dense_model_default, "Fallback Defaults"

    @property
    def cheap_model(self) -> str:
        return self.get_resolved_models()[0]

    @property
    def dense_model(self) -> str:
        return self.get_resolved_models()[1]

    def validate_production(self) -> None:
        """
        Performs pre-flight environment checks to ensure required production keys are set.
        """
        if not self.fireworks_api_key:
            raise ValueError("Environment configuration error: FIREWORKS_API_KEY must be set.")
        
        # Trigger allowed_models property validation
        allowed = self.allowed_models
        cheap, dense, _ = self.get_resolved_models()
        
        if allowed:
            if cheap not in allowed:
                raise ValueError(
                    f"Configuration error: Cheap model '{cheap}' is not in ALLOWED_MODELS: {allowed}"
                )
            if dense not in allowed:
                raise ValueError(
                    f"Configuration error: Dense model '{dense}' is not in ALLOWED_MODELS: {allowed}"
                )
        else:
            print(
                f"Notice: ALLOWED_MODELS is not set. Falling back to default Fireworks models:\n"
                f"  Cheap model -> {cheap}\n"
                f"  Dense model -> {dense}\n"
                f"Ensure these models are accessible for your Fireworks account.",
                file=sys.stderr
            )
                
    def print_startup_summary(self) -> None:
        """
        Outputs the Fireworks model discovery configuration overview to stdout.
        """
        allowed = self.allowed_models
        cheap, dense, method = self.get_resolved_models()
        
        # Categorize allowed models for print summary
        cheap_tier = []
        medium_tier = []
        dense_tier = []
        
        for m in allowed:
            tier, _ = get_model_capability_key(m)
            if tier == 0:
                cheap_tier.append(m)
            elif tier == 1:
                medium_tier.append(m)
            else:
                dense_tier.append(m)
                
        print("====================================================")
        print("Fireworks Model Discovery")
        print("====================================================")
        print(f"Allowed Models:     {', '.join(allowed) if allowed else 'None'}")
        print(f"Detected Cheap Tier:  {', '.join(cheap_tier) if cheap_tier else 'None'}")
        print(f"Detected Medium Tier: {', '.join(medium_tier) if medium_tier else 'None'}")
        print(f"Detected Dense Tier:  {', '.join(dense_tier) if dense_tier else 'None'}")
        print("----------------------------------------------------")
        print(f"Selected Cheap Model: {cheap}")
        print(f"Selected Dense Model: {dense}")
        print(f"Selection Method:     {method}")
        print("====================================================")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

# Print startup log overview if ALLOWED_MODELS is populated in the environment
if os.environ.get("ALLOWED_MODELS") is not None:
    try:
        settings.print_startup_summary()
    except Exception:
        pass
