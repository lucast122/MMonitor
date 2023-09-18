import gzip
from collections import defaultdict

import numpy as np
from Bio import SeqIO


class FastqStatistics:

    def __init__(self, file_path):

        self.file_path = file_path
        self.sequences = []
        self.qualities = []
        self.lengths = []
        self.gc_contents = []
        # Detect if it's a gzipped file based on the file extension

        self.load_file()

    def load_file(self):
        is_gzipped = self.file_path.endswith(".gz")
        open_func = gzip.open if is_gzipped else open
        mode = 'rt' if is_gzipped else 'r'
        with open_func(self.file_path, mode) as f:
            for record in SeqIO.parse(f, "fastq"):
                self.sequences.append(record.seq)
                self.qualities.append(record.letter_annotations["phred_quality"])
                self.lengths.append(len(record.seq))


        if not self.qualities:
            raise ValueError("Quality scores list is empty!")

    def number_of_reads(self):
        return len(self.sequences)

    def total_bases_sequenced(self):
        return sum(self.lengths)

    def q20_q30_scores(self):
        total_bases = sum(self.lengths)
        q20_bases = sum(1 for quality in self.qualities for q in quality if q >= 20)
        q30_bases = sum(1 for quality in self.qualities for q in quality if q >= 30)
        return (q20_bases / total_bases) * 100, (q30_bases / total_bases) * 100

    def quality_score_distribution(self):
        # Average quality per read
        avg_quality_per_read = [np.mean(quality) for quality in self.qualities]

        # Base quality distribution for each base position
        base_quality_distribution = defaultdict(list)
        for quality in self.qualities:
            for i, q in enumerate(quality):
                base_quality_distribution[i].append(q)

        threshold = len(self.qualities) * 0.5  # only distribution for bases that are covered at least by 50% of reads
        base_quality_avg = {position: np.mean(qualities)
                            for position, qualities in base_quality_distribution.items()
                            if len(qualities) >= threshold}


        return avg_quality_per_read, base_quality_avg

    def gc_content(self):
        """Compute the GC content of the sequences."""
        total_bases = sum(self.lengths)
        g_count = sum(seq.count('G') for seq in self.sequences)
        c_count = sum(seq.count('C') for seq in self.sequences)

        return (g_count + c_count) / total_bases

    def read_lengths_statistics(self):
        lengths = [len(seq) for seq in self.sequences]
        return {
            'min_length': min(lengths),
            'max_length': max(lengths),
            'mean_length': np.mean(lengths),
            'median_length': np.median(lengths)
        }

    def quality_statistics(self):
        if not self.qualities:
            raise ValueError("Quality scores list is empty!")

        all_quality_scores = [score for sublist in self.qualities for score in sublist]

        return {
            'min_quality': min(all_quality_scores),
            'max_quality': max(all_quality_scores),
            'mean_quality': sum(all_quality_scores) / len(all_quality_scores),
        }

    def qualities_vs_lengths(self):
        avg_qualities = [sum(quals) / len(quals) for quals in self.qualities]
        return {
            'read_lengths': self.lengths,
            'avg_qualities': avg_qualities
        }

    def gc_content_per_sequence(self):
        """Compute the GC content for each sequence."""
        self.gc_contents = [(seq.count('G') + seq.count('C')) / len(seq) for seq in self.sequences]
        return self.gc_contents
