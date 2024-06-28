import gzip
import time
from collections import defaultdict
import numpy as np
from Bio import SeqIO
from concurrent.futures import ThreadPoolExecutor

class FastqStatistics:

    def __init__(self, file_path, multi=False, num_threads=64):
        print(f"Calculating statistics for {file_path}")
        self.file_path = file_path
        self.sequences = []
        self.qualities = []
        self.lengths = []
        self.gc_contents = []

        if multi:
            start_time = time.time()
            self.load_files_threaded(self.file_path, num_threads)
            end_time = time.time()
            print(f"Loaded files in {end_time - start_time} seconds")
        else:
            start_time = time.time()
            self.load_file(file_path)
            end_time = time.time()
            print(f"Loaded file in {end_time - start_time} seconds")

    def load_files_threaded(self, file_paths, num_threads):
        print(f"Loading files: {file_paths}")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for file_path in file_paths:
                futures.append(executor.submit(self.load_file, file_path))
            for future in futures:
                future.result()

    def load_file(self, file_path):

        print(f"Attempting to load file: {file_path}")
        if file_path is None:
            file_path = self.file_path


        is_gzipped = file_path.endswith(".gz")
        open_func = gzip.open if is_gzipped else open
        mode = 'rt' if is_gzipped else 'r'

        with open_func(file_path, mode) as f:
            for record in SeqIO.parse(f, "fastq"):
                self.sequences.append(record.seq)
                self.qualities.append(record.letter_annotations["phred_quality"])
                self.lengths.append(len(record.seq))

        if not self.qualities:
            raise ValueError("Quality scores list is empty!")

    def number_of_reads(self):
        start_time = time.time()
        result = len(self.sequences)
        end_time = time.time()
        print(f"Number of reads calculated in {end_time - start_time} seconds")
        return result

    def total_bases_sequenced(self):
        start_time = time.time()
        result = sum(self.lengths)
        end_time = time.time()
        print(f"Total bases sequenced calculated in {end_time - start_time} seconds")
        return result

    def q20_q30_scores(self):
        start_time = time.time()
        total_bases = sum(self.lengths)
        q20_bases = sum(1 for quality in self.qualities for q in quality if q >= 20)
        q30_bases = sum(1 for quality in self.qualities for q in quality if q >= 30)
        q20_percentage = (q20_bases / total_bases) * 100
        q30_percentage = (q30_bases / total_bases) * 100
        end_time = time.time()
        print(f"Q20/Q30 scores calculated in {end_time - start_time} seconds")
        return q20_percentage, q30_percentage

    def quality_score_distribution(self):
        start_time = time.time()
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

        end_time = time.time()
        print(f"Quality score distribution calculated in {end_time - start_time} seconds")
        return avg_quality_per_read, base_quality_avg

    def gc_content(self):
        start_time = time.time()
        total_bases = sum(self.lengths)
        g_count = sum(seq.count('G') for seq in self.sequences)
        c_count = sum(seq.count('C') for seq in self.sequences)
        gc_percentage = (g_count + c_count) / total_bases
        end_time = time.time()
        print(f"GC content calculated in {end_time - start_time} seconds")
        return gc_percentage

    def read_lengths_statistics(self):
        start_time = time.time()
        lengths = [len(seq) for seq in self.sequences]
        result = {
            'min_length': min(lengths),
            'max_length': max(lengths),
            'mean_length': np.mean(lengths),
            'median_length': np.median(lengths)
        }
        end_time = time.time()
        print(f"Read lengths statistics calculated in {end_time - start_time} seconds")
        return result

    def quality_statistics(self):
        if not self.qualities:
            raise ValueError("Quality scores list is empty!")

        start_time = time.time()
        all_quality_scores = [score for sublist in self.qualities for score in sublist]
        result = {
            'min_quality': min(all_quality_scores),
            'max_quality': max(all_quality_scores),
            'mean_quality': sum(all_quality_scores) / len(all_quality_scores),
        }
        end_time = time.time()
        print(f"Quality statistics calculated in {end_time - start_time} seconds")
        return result

    def qualities_vs_lengths(self):
        start_time = time.time()
        avg_qualities = [sum(quals) / len(quals) for quals in self.qualities]
        result = {
            'read_lengths': self.lengths,
            'avg_qualities': avg_qualities
        }
        end_time = time.time()
        print(f"Qualities vs. lengths calculated in {end_time - start_time} seconds")
        return result

    def gc_content_per_sequence(self):
        start_time = time.time()
        self.gc_contents = [(seq.count('G') + seq.count('C')) / len(seq) for seq in self.sequences]
        end_time = time.time()
        print(f"GC content per sequence calculated in {end_time - start_time} seconds")
        return self.gc_contents

