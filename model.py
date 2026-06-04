import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


TOKEN_RE = re.compile(r"[a-zA-Z']+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "do",
    "for",
    "here",
    "i",
    "in",
    "is",
    "it",
    "me",
    "not",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "this",
    "to",
    "we",
    "you",
    "your",
}

HARM_CATEGORIES = {
    "harassment": {
        "label": "Harassment",
        "terms": {
            "loser",
            "worthless",
            "pathetic",
            "annoying",
            "nobody",
            "block",
            "laugh",
            "ashamed",
            "joke",
        },
    },
    "hate_speech": {
        "label": "Hate Speech",
        "terms": {
            "hate",
            "disgusting",
            "race",
            "religion",
            "gender",
            "slur",
            "inferior",
            "community",
        },
    },
    "threat": {
        "label": "Threat",
        "terms": {
            "kill",
            "hurt",
            "destroy",
            "attack",
            "threat",
            "fear",
            "fail",
            "dead",
        },
    },
    "insult": {
        "label": "Insult",
        "terms": {
            "stupid",
            "dumb",
            "idiot",
            "ugly",
            "trash",
            "fool",
            "useless",
        },
    },
    "exclusion": {
        "label": "Exclusion",
        "terms": {
            "away",
            "alone",
            "belong",
            "lost",
            "leave",
            "unwelcome",
            "group",
            "ignore",
        },
    },
}

CATEGORY_ORDER = ["harassment", "hate_speech", "threat", "insult", "exclusion"]


def tokenize(text):
    return [token.lower().strip("'") for token in TOKEN_RE.findall(text)]


class CyberbullyingClassifier:
    def __init__(self):
        self.class_counts = Counter()
        self.word_counts = defaultdict(Counter)
        self.total_words = Counter()
        self.vocabulary = set()
        self.labels = []

    def train(self, rows):
        for label, text in rows:
            tokens = tokenize(text)
            self.class_counts[label] += 1
            self.word_counts[label].update(tokens)
            self.total_words[label] += len(tokens)
            self.vocabulary.update(tokens)

        self.labels = sorted(self.class_counts)

    def predict(self, text):
        tokens = tokenize(text)
        if not tokens:
            return {
                "label": "non_bullying",
                "category": "safe",
                "category_label": "Safe",
                "danger_level": "Safe",
                "confidence": 0,
                "scores": {"bullying": 0, "non_bullying": 1},
                "keywords": [],
                "explanation": "Enter a message to begin the safety analysis.",
                "is_bullying": False,
            }

        total_docs = sum(self.class_counts.values())
        vocab_size = max(len(self.vocabulary), 1)
        log_scores = {}

        for label in self.labels:
            prior = self.class_counts[label] / total_docs
            score = math.log(prior)

            for token in tokens:
                word_frequency = self.word_counts[label][token] + 1
                denominator = self.total_words[label] + vocab_size
                score += math.log(word_frequency / denominator)

            log_scores[label] = score

        probabilities = self._normalize(log_scores)
        label = max(probabilities, key=probabilities.get)
        bullying_probability = probabilities.get("bullying", 0)
        confidence = round(probabilities[label] * 100, 2)
        category, matched_terms = self._classify_category(tokens, bullying_probability)
        danger_level = self._danger_level(bullying_probability, category)
        keywords = self._top_signal_words(tokens, matched_terms)
        is_bullying = danger_level != "Safe"

        return {
            "label": label,
            "category": category,
            "category_label": self._category_label(category),
            "danger_level": danger_level,
            "confidence": confidence,
            "danger_score": round(bullying_probability * 100, 2),
            "scores": probabilities,
            "keywords": keywords,
            "explanation": self._explain(category, danger_level, keywords, bullying_probability),
            "is_bullying": is_bullying,
        }

    def _normalize(self, log_scores):
        max_score = max(log_scores.values())
        exp_scores = {
            label: math.exp(score - max_score) for label, score in log_scores.items()
        }
        total = sum(exp_scores.values())
        return {label: value / total for label, value in exp_scores.items()}

    def _classify_category(self, tokens, bullying_probability):
        category_scores = {}

        for category in CATEGORY_ORDER:
            terms = HARM_CATEGORIES[category]["terms"]
            matches = sorted({token for token in tokens if token in terms})
            category_scores[category] = (len(matches), matches)

        category, (score, matches) = max(
            category_scores.items(),
            key=lambda item: (item[1][0], CATEGORY_ORDER.index(item[0]) * -1),
        )

        if bullying_probability < 0.45 and score == 0:
            return "safe", []

        if score == 0:
            return "harassment", []

        return category, matches

    def _category_label(self, category):
        if category == "safe":
            return "Safe"
        return HARM_CATEGORIES[category]["label"]

    def _danger_level(self, bullying_probability, category):
        if category == "safe" or bullying_probability < 0.45:
            return "Safe"
        if bullying_probability >= 0.88:
            return "Critical"
        if bullying_probability >= 0.72:
            return "High"
        if bullying_probability >= 0.56:
            return "Medium"
        return "Low"

    def _explain(self, category, danger_level, keywords, bullying_probability):
        if category == "safe":
            return "The message appears respectful or non-abusive based on the model score and keyword scan."

        keyword_text = ", ".join(keywords[:4]) if keywords else "general negative phrasing"
        probability = round(bullying_probability * 100, 1)
        return (
            f"{danger_level} risk: the message matches {self._category_label(category).lower()} "
            f"patterns with a bullying score of {probability}%. Flagged signals include {keyword_text}."
        )

    def _top_signal_words(self, tokens, matched_terms=None):
        signals = []
        matched_terms = matched_terms or []
        vocab_size = max(len(self.vocabulary), 1)

        for token in set(tokens):
            if token in STOPWORDS:
                continue
            bullying_count = self.word_counts["bullying"][token] + 1
            non_count = self.word_counts["non_bullying"][token] + 1
            bullying_rate = bullying_count / (self.total_words["bullying"] + vocab_size)
            non_rate = non_count / (self.total_words["non_bullying"] + vocab_size)
            lift = bullying_rate / non_rate
            if lift > 1.15:
                signals.append((token, lift))

        ranked = [word for word, _ in sorted(signals, key=lambda item: item[1], reverse=True)]
        combined = list(dict.fromkeys([*matched_terms, *ranked]))
        return combined[:6]


def load_dataset(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            label = row["label"].strip()
            text = row["text"].strip()
            if label and text:
                rows.append((label, text))
    return rows


def build_classifier(dataset_path="data/messages.csv"):
    classifier = CyberbullyingClassifier()
    classifier.train(load_dataset(dataset_path))
    return classifier
