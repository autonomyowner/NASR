"""
LocalAgreement-2 Algorithm Implementation
Word stability filtering to minimize retractions in streaming STT
"""

import time
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WordCandidate:
    """Candidate word with metadata"""
    word: str
    confidence: float
    start_time: float
    end_time: float
    position: int
    source_transcription_id: str


@dataclass 
class StableWord:
    """Confirmed stable word"""
    word: str
    confidence: float
    start_time: float
    end_time: float
    position: int
    agreement_count: int
    first_seen: float
    confirmed_at: float


class LocalAgreement2:
    """
    LocalAgreement-2 algorithm for word stability in streaming STT.
    
    Minimizes word retractions by requiring agreement across multiple
    transcription hypotheses before confirming words.
    """
    
    def __init__(
        self,
        agreement_threshold: int = 2,
        stability_window: int = 3,
        confidence_threshold: float = 0.7,
        max_position_drift: int = 2,
        temporal_window_ms: float = 1000.0
    ):
        """
        Initialize LocalAgreement-2 filter.
        
        Args:
            agreement_threshold: Minimum times word must appear to confirm
            stability_window: Number of recent transcriptions to consider
            confidence_threshold: Minimum confidence for word consideration
            max_position_drift: Max position change allowed for same word
            temporal_window_ms: Time window for temporal alignment
        """
        self.agreement_threshold = agreement_threshold
        self.stability_window = stability_window
        self.confidence_threshold = confidence_threshold
        self.max_position_drift = max_position_drift
        self.temporal_window = temporal_window_ms / 1000.0
        
        # State tracking
        self.confirmed_words: List[StableWord] = []
        self.candidate_history: List[List[WordCandidate]] = []
        self.transcription_counter = 0
        self.last_cleanup = time.time()
        
        # Performance metrics
        self.total_candidates = 0
        self.total_confirmed = 0
        self.total_retractions = 0
        
    def process_transcription(
        self, 
        words: List[str], 
        confidences: List[float],
        timestamps: Optional[List[Tuple[float, float]]] = None
    ) -> Tuple[List[str], List[str], bool]:
        """
        Process new transcription and return interim/confirmed words.
        
        Args:
            words: List of transcribed words
            confidences: Confidence scores for each word
            timestamps: Optional (start, end) timestamps for each word
            
        Returns:
            (interim_words, newly_confirmed_words, has_new_confirmations)
        """
        self.transcription_counter += 1
        current_time = time.time()
        
        # Create word candidates
        candidates = []
        for i, (word, conf) in enumerate(zip(words, confidences)):
            if conf >= self.confidence_threshold:
                start_time = timestamps[i][0] if timestamps and i < len(timestamps) else current_time
                end_time = timestamps[i][1] if timestamps and i < len(timestamps) else current_time
                
                candidate = WordCandidate(
                    word=word.strip().lower(),
                    confidence=conf,
                    start_time=start_time,
                    end_time=end_time,
                    position=i,
                    source_transcription_id=str(self.transcription_counter)
                )
                candidates.append(candidate)
                
        self.candidate_history.append(candidates)
        self.total_candidates += len(candidates)
        
        # Maintain window size
        if len(self.candidate_history) > self.stability_window:
            self.candidate_history.pop(0)
            
        # Find newly confirmed words
        newly_confirmed = self._find_stable_words()
        
        # Build response
        interim_words = [c.word for c in candidates]
        confirmed_words = [w.word for w in newly_confirmed]
        has_new = len(newly_confirmed) > 0
        
        self.total_confirmed += len(newly_confirmed)
        
        # Periodic cleanup
        if current_time - self.last_cleanup > 5.0:
            self._cleanup_old_confirmations()
            self.last_cleanup = current_time
            
        logger.debug(f"Processed {len(words)} words, confirmed {len(newly_confirmed)}")
        
        return interim_words, confirmed_words, has_new
    
    def _find_stable_words(self) -> List[StableWord]:
        """Find words that meet stability criteria"""
        if len(self.candidate_history) < self.agreement_threshold:
            return []
            
        newly_confirmed = []
        current_time = time.time()
        
        # Group candidates by word and position similarity
        word_groups = self._group_candidates_by_similarity()
        
        for word, candidate_groups in word_groups.items():
            for position_group in candidate_groups:
                # Check if this group meets agreement threshold
                if len(position_group) >= self.agreement_threshold:
                    
                    # Verify not already confirmed at this position
                    if self._is_already_confirmed(word, position_group[0].position):
                        continue
                        
                    # Calculate aggregate properties
                    avg_confidence = sum(c.confidence for c in position_group) / len(position_group)
                    avg_start = sum(c.start_time for c in position_group) / len(position_group)
                    avg_end = sum(c.end_time for c in position_group) / len(position_group)
                    first_seen = min(c.start_time for c in position_group)
                    
                    stable_word = StableWord(
                        word=word,
                        confidence=avg_confidence,
                        start_time=avg_start,
                        end_time=avg_end,
                        position=position_group[0].position,
                        agreement_count=len(position_group),
                        first_seen=first_seen,
                        confirmed_at=current_time
                    )
                    
                    self.confirmed_words.append(stable_word)
                    newly_confirmed.append(stable_word)
                    
        return newly_confirmed
    
    def _group_candidates_by_similarity(self) -> Dict[str, List[List[WordCandidate]]]:
        """Group candidates by word and position similarity"""
        word_groups = defaultdict(list)
        
        # Collect all candidates
        all_candidates = []
        for candidates in self.candidate_history:
            all_candidates.extend(candidates)
            
        # Group by word
        by_word = defaultdict(list)
        for candidate in all_candidates:
            by_word[candidate.word].append(candidate)
            
        # Sub-group by position similarity
        for word, candidates in by_word.items():
            position_groups = []
            
            for candidate in candidates:
                # Find existing group with similar position
                assigned = False
                for group in position_groups:
                    if any(abs(candidate.position - c.position) <= self.max_position_drift 
                          for c in group):
                        group.append(candidate)
                        assigned = True
                        break
                        
                if not assigned:
                    position_groups.append([candidate])
                    
            word_groups[word] = position_groups
            
        return word_groups
    
    def _is_already_confirmed(self, word: str, position: int) -> bool:
        """Check if word at position is already confirmed"""
        for confirmed in self.confirmed_words:
            if (confirmed.word == word and 
                abs(confirmed.position - position) <= self.max_position_drift):
                return True
        return False
    
    def _cleanup_old_confirmations(self):
        """Remove old confirmed words to prevent memory growth"""
        current_time = time.time()
        cutoff_time = current_time - (self.temporal_window * 10)  # Keep 10x temporal window
        
        initial_count = len(self.confirmed_words)
        self.confirmed_words = [
            w for w in self.confirmed_words 
            if w.confirmed_at > cutoff_time
        ]
        
        cleaned = initial_count - len(self.confirmed_words)
        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} old confirmed words")
    
    def get_all_confirmed_words(self) -> List[str]:
        """Get all confirmed words in order"""
        sorted_words = sorted(self.confirmed_words, key=lambda w: w.position)
        return [w.word for w in sorted_words]
    
    def get_confirmation_stats(self) -> Dict:
        """Get performance statistics"""
        retraction_rate = (
            self.total_retractions / self.total_confirmed 
            if self.total_confirmed > 0 else 0.0
        )
        
        confirmation_rate = (
            self.total_confirmed / self.total_candidates 
            if self.total_candidates > 0 else 0.0
        )
        
        return {
            "total_candidates": self.total_candidates,
            "total_confirmed": self.total_confirmed,
            "total_retractions": self.total_retractions,
            "retraction_rate": retraction_rate,
            "confirmation_rate": confirmation_rate,
            "active_confirmed_words": len(self.confirmed_words),
            "agreement_threshold": self.agreement_threshold,
            "stability_window": self.stability_window
        }
    
    def reset(self):
        """Reset algorithm state"""
        self.confirmed_words.clear()
        self.candidate_history.clear()
        self.transcription_counter = 0
        self.total_candidates = 0
        self.total_confirmed = 0
        self.total_retractions = 0
        logger.info("LocalAgreement-2 state reset")
    
    def finalize_session(self) -> List[StableWord]:
        """Finalize session and return any remaining stable words"""
        # Process final candidates with relaxed threshold
        original_threshold = self.agreement_threshold
        self.agreement_threshold = max(1, self.agreement_threshold - 1)
        
        final_words = self._find_stable_words()
        
        # Restore original threshold
        self.agreement_threshold = original_threshold
        
        logger.info(f"Session finalized with {len(final_words)} final words")
        return final_words