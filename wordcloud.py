import re
import tomllib
from collections import Counter
from pathlib import Path

import nltk
import numpy as np
import typer
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from PIL import Image
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.table import Column, Table

from wordcloud import WordCloud

nltk.download("wordnet", quiet=True)
# nltk.download('omw-1.4')

settings_path = Path("data/settings.toml")
settings = tomllib.loads(settings_path.read_text())

app = typer.Typer()


def read_file(filename):
    """Read the contents of a file and return them."""
    with open(filename, "r") as file:
        return file.read()


def remove_stopwords(words, additional_stop_words):
    """Remove stopwords and non-alphanumeric words from a list of words."""
    stop_words = set(stopwords.words("portuguese"))
    if additional_stop_words:
        stop_words.update(additional_stop_words)

    # some words are automattically considered stop_words,
    # but you might want to include them anyways.
    keep_stop_words = settings["keep_stop_words"]
    if keep_stop_words:
        for keep_word in keep_stop_words:
            stop_words.discard(keep_word)

    return [w for w in words if w not in stop_words and w.isalnum()]


def replace_laughter(words, laughter_patterns):
    """Replace specified laughter patterns with a single common representation."""
    if not laughter_patterns:
        laughter_patterns = ["(ha){2,}", "rofl", "lol"]
    laughter_pattern = "|".join(f"({pattern})" for pattern in laughter_patterns)
    laughter_replacement = settings["laughter_replacement"] if settings["laughter_replacement"] else "LOL"
    return [w if not re.match(laughter_pattern, w) else laughter_replacement for w in words]


def normalize_words(words, normalize_patterns):
    """Replace specified patterns with a single common representation."""
    normalized_words = []
    for word in words:
        for replacement, patterns in normalize_patterns.items():
            normalized_pattern = "|".join(f"({pattern})" for pattern in patterns)
            if re.match(normalized_pattern, word):
                normalized_words.append(replacement)
                break  # Stop after finding the first replacement match
        else:
            normalized_words.append(word)  # No replacement found, keep the word unchanged
    return normalized_words


def preprocess_text(content):
    """Preprocess the text content by tokenizing and removing stopwords."""
    words = nltk.word_tokenize(content.lower())
    
    additional_stop_words = settings["include_stop_words"]
    filtered_words = remove_stopwords(words, additional_stop_words)
    
    laughter_patterns = settings["laughter_patterns"]
    filtered_laughter = replace_laughter(filtered_words, laughter_patterns)

    normalize_patterns = settings["normalize_patterns"]
    normalized = normalize_words(filtered_laughter, normalize_patterns)

    return normalized


def get_wordnet_pos(word):
    """Map a POS tag to WordNet POS tag for lemmatization."""
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wordnet.ADJ, "N": wordnet.NOUN, "V": wordnet.VERB, "R": wordnet.ADV}

    return tag_dict.get(tag, wordnet.NOUN)


def print_word_frequency_table(lemmatized_corpus):
    """Print the word frequency table using rich."""
    word_freq = Counter(lemmatized_corpus)

    # Filter and sort words with 30 or more appearances in decreasing order
    filtered_word_freq = {word: freq for word, freq in word_freq.items() if freq >= 30}
    sorted_filtered_word_freq = dict(sorted(filtered_word_freq.items(), key=lambda item: item[1], reverse=True))

    table = Table(title="[bold underline]Word Frequency Table[/]")
    table.add_column("Word", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")

    for word, freq in sorted_filtered_word_freq.items():
        table.add_row(word, str(freq))

    console = Console()
    console.print("\n[bold underline]Word Frequency Table[/]\n")
    console.print(table)


@app.command()
def main(wordcloud_file: str):
    """Generate a word cloud from a text file."""

    # Create a progress bar for the word cloud generation
    text_column = TextColumn("{task.description}", table_column=Column(ratio=1))
    bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
    progress = Progress(text_column, bar_column, TaskProgressColumn(), expand=True)

    with progress:
        task = progress.add_task("[cyan]Generating wordcloud...", total=5)
        progress.update(task, completed=1)

        corpus = preprocess_text(read_file(f"data/{wordcloud_file}"))
        progress.update(task, completed=2)
    
        lemmatizer = WordNetLemmatizer()
        lemmatized_corpus = [lemmatizer.lemmatize(w, get_wordnet_pos(w)) for w in corpus]
        unique_string = " ".join(lemmatized_corpus)
        progress.update(task, completed=3)

        cloud_mask = np.array(Image.open("cloud.png"))
        wordcloud = WordCloud(
            width=1100,
            height=680,
            background_color="black",
            mask=cloud_mask,
            max_words=500,
            contour_width=2,
            contour_color="green",
        )
        progress.update(task, completed=4)

        wordcloud.generate(unique_string)
        progress.update(task, completed=5)

    output_file = Path(wordcloud_file).stem
    wordcloud.to_file(f"output/{output_file}.png")

    

    # Print the word frequency table using the separate function
    print_word_frequency_table(lemmatized_corpus)


if __name__ == "__main__":
    app()
