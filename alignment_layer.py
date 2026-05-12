"""
PersonaVLM POC — Response Alignment Layer
Adapts output based on learned user preferences.
Demonstrates how PersonaVLM transforms generic LLM responses into
personalized outputs aligned with individual communication patterns.
"""
import re
from memory_layer import retrieve_memories


class ResponseAligner:
    """
    Aligns generated responses to match user's established patterns.
    In production, this would be a fine-tuned alignment layer.
    Here we demonstrate the concept through rule-based adaptation
    that mirrors how PersonaVLM would use stored preferences.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> dict:
        memories = retrieve_memories(self.user_id, memory_type="preference")
        prefs = {
            "tone": "neutral",
            "length": "medium",
            "greeting": "",
            "signoff": "Best",
            "formality": "medium",
            "style_notes": [],
        }
        for m in memories:
            content = m["content"].lower()
            if "concise" in content or "terse" in content or "short" in content:
                prefs["length"] = "short"
                prefs["tone"] = "direct"
            if "verbose" in content or "detailed" in content or "thorough" in content:
                prefs["length"] = "long"
            if "warm" in content or "friendly" in content or "casual" in content:
                prefs["tone"] = "warm"
                prefs["formality"] = "low"
            if "formal" in content or "professional" in content:
                prefs["tone"] = "professional"
                prefs["formality"] = "high"
            if "regards" in content:
                prefs["signoff"] = "Regards"
            if "best" in content:
                prefs["signoff"] = "Best"
            if "cheers" in content:
                prefs["signoff"] = "Cheers"
            if "hey" in content:
                prefs["greeting"] = "Hey"
            if "hi" in content:
                prefs["greeting"] = "Hi"
        return prefs

    def align_email(self, draft: str, recipient_context: str = "") -> dict:
        """
        Align a draft email to the user's style.
        Returns the aligned version + metadata about what changed.
        """
        changes = []
        aligned = draft

        # Length adjustment
        if self.preferences["length"] == "short":
            words = aligned.split()
            original_len = len(words)
            if len(words) > 50:
                # Truncate verbose language
                aligned = re.sub(r'\bin order to\b', 'to', aligned, flags=re.IGNORECASE)
                aligned = re.sub(r'\bi would like to inform you that\b', '', aligned, flags=re.IGNORECASE)
                aligned = re.sub(r'\bplease be advised that\b', '', aligned, flags=re.IGNORECASE)
                aligned = re.sub(r'\badditionally,\b', 'Also,', aligned, flags=re.IGNORECASE)
                aligned = re.sub(r'\bfurthermore,\b', 'Also,', aligned, flags=re.IGNORECASE)
                if len(aligned.split()) > 50:
                    aligned = ' '.join(words[:50]) + "...[truncated for brevity]"
                changes.append(f"Length: {original_len} → {len(aligned.split())} words")

        # Tone adjustment
        if self.preferences["tone"] == "concise" and self.preferences["tone"] == "direct":
            aligned = aligned.replace("I think we should", "Let's")
            aligned = aligned.replace("I would suggest that", "Suggest")
            aligned = aligned.replace("It would be great if you could", "Please")
            changes.append("Tone: made more direct")

        # Greeting/signoff
        if self.preferences["greeting"] and "Hi" in aligned[:20]:
            aligned = aligned.replace("Hi", self.preferences["greeting"], 1)
            changes.append(f"Greeting → {self.preferences['greeting']}")

        # Signoff replacement
        signoff_match = re.search(r'(Best|Regards|Cheers|Thanks|Sincerely),', aligned)
        if signoff_match and signoff_match.group(1) != self.preferences["signoff"]:
            orig = signoff_match.group(1)
            aligned = aligned.replace(f"{orig},", f"{self.preferences['signoff']},")
            changes.append(f"Signoff: {orig} → {self.preferences['signoff']}")

        return {
            "original": draft,
            "aligned": aligned,
            "applied_preferences": {
                "tone": self.preferences["tone"],
                "length": self.preferences["length"],
                "signoff": self.preferences["signoff"],
                "formality": self.preferences["formality"],
            },
            "changes_made": changes if changes else ["Style already matches preferences"],
            "alignment_confidence": min(1.0, len(self.preferences["style_notes"]) / 5 + 0.5),
        }

    def get_alignment_profile(self) -> dict:
        """Return the user's alignment profile."""
        return self.preferences


def demo_alignment_scenarios(aligner: ResponseAligner) -> list[dict]:
    """Demonstrate alignment on example scenarios."""
    scenarios = [
        {
            "scenario": "Reply to vendor about pricing",
            "recipient_type": "vendor",
            "draft": (
                "Hi there,\n\n"
                "I hope this message finds you well. I am writing to inform you that "
                "we would like to discuss the pricing proposal you sent over last week. "
                "Additionally, we would appreciate it if you could provide us with more "
                "detailed breakdowns of each line item. Furthermore, please let us know "
                "if there are any volume discounts available.\n\n"
                "We look forward to hearing from you at your earliest convenience.\n\n"
                "Best regards,\n"
            ),
        },
        {
            "scenario": "Reply to co-founder about strategy",
            "recipient_type": "co-founder",
            "draft": (
                "Hey,\n\n"
                "I think we should definitely consider the Series A timeline you "
                "mentioned. In order to be fully prepared, I would suggest that we "
                "start building out the data room next month. Let me know what you think.\n\n"
                "Cheers,\n"
            ),
        },
    ]

    results = []
    for s in scenarios:
        result = aligner.align_email(s["draft"], s["recipient_type"])
        result["scenario"] = s["scenario"]
        result["recipient_type"] = s["recipient_type"]
        results.append(result)

    return results
