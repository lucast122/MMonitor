import gzip
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from Bio import SeqIO


class FastqStatistics:

    def __init__(self, file_paths, multi=False, num_threads=64):
        self.file_paths = file_paths if isinstance(file_paths, list) else [file_paths]
        self.sequences = []  # Keep if sequence data needed beyond statistics
        self.qualities = []  # Converted to numpy arrays for efficient processing
        self.lengths = np.array([], dtype=int)
        self.gc_counts = np.array([], dtype=int)
        self.q20_counts = np.array([], dtype=int)
        self.q30_counts = np.array([], dtype=int)
        self.total_bases = 0
        self.load_files(multi, num_threads)

    def load_files(self, multi, num_threads):
        start_time = time.time()
        if multi:
            self.load_files_threaded(num_threads)
        else:
            for file_path in self.file_paths:
                self.load_file(file_path)
        end_time = time.time()
        print(f"Loaded files in {end_time - start_time} seconds")

    def load_files_threaded(self, num_threads):
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            executor.map(self.load_file, self.file_paths)

    def load_file(self, file_path):
        is_gzipped = file_path.endswith(".gz")
        with (gzip.open(file_path, 'rt') if is_gzipped else open(file_path, 'r')) as f:
            for record in SeqIO.parse(f, "fastq"):
                seq = str(record.seq)
                self.sequences.append(seq)  # Optional, based on need
                quality_scores = np.array(record.letter_annotations["phred_quality"], dtype=int)
                self.qualities.append(quality_scores)
                self.lengths = np.append(self.lengths, len(seq))
                self.gc_counts = np.append(self.gc_counts, seq.count('G') + seq.count('C'))
                self.q20_counts = np.append(self.q20_counts, np.sum(quality_scores >= 20))
                self.q30_counts = np.append(self.q30_counts, np.sum(quality_scores >= 30))
        self.total_bases += self.lengths.sum()

    def number_of_reads(self):
        return len(self.sequences)

    def total_bases_sequenced(self):
        return self.total_bases

    def q20_q30_scores(self):
        q20_percentage = (self.q20_counts.sum() / self.total_bases) * 100
        q30_percentage = (self.q30_counts.sum() / self.total_bases) * 100
        return q20_percentage, q30_percentage

    def gc_content(self):
        return (self.gc_counts.sum() / self.total_bases) * 100

    def read_lengths_statistics(self):
        if len(self.lengths) == 0:
            return {}
        return {
            'min_length': np.min(self.lengths),
            'max_length': np.max(self.lengths),
            'mean_length': np.mean(self.lengths),
            'median_length': np.median(self.lengths)
        }

    def quality_statistics(self):
        all_quality_scores = np.concatenate(self.qualities)
        return {
            'min_quality': np.min(all_quality_scores),
            'max_quality': np.max(all_quality_scores),
            'mean_quality': np.mean(all_quality_scores),
        }

    def qualities_vs_lengths(self):
        avg_qualities = [np.mean(quals) for quals in self.qualities]
        return {
            'read_lengths': self.lengths.tolist(),
            'avg_qualities': avg_qualities
        }

    def gc_content_per_sequence(self):
        gc_contents = (self.gc_counts / self.lengths) * 100
        return gc_contents.tolist()
