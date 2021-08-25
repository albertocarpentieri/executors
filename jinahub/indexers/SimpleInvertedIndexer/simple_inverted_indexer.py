import os
import operator
from typing import Optional, Dict, Tuple, List
from collections import defaultdict
import pickle
from sklearn.feature_extraction.text import CountVectorizer
from scipy.sparse import csr_matrix

import numpy as np

from jina import Executor, DocumentArray, requests, Document
from jina.types.arrays.memmap import DocumentArrayMemmap
from jina_commons import get_logger


class InvertedIndex:

    def __init__(self):
        self.inverted_index = defaultdict(set)
        self.document_frequencies = defaultdict(int)
        self.document_sparse_vectors = {}
        self.idfs = {}

    def cache_idfs(self):
        for term_idx in self.document_frequencies.keys():
            num = len(self.document_sparse_vectors.keys())
            den = 1 + self.document_frequencies[term_idx]
            self.idfs[term_idx] = np.log(num / den)

    def add(self, document_id, document_vector):
        def _add(term_id, doc_id, value):
            self.inverted_index[term_id].add(doc_id)
            self.document_frequencies[term_id] += value

        for term_id, term_value in zip(document_vector.indices, document_vector.data):
            _add(term_id, document_id, term_value)
        self.document_sparse_vectors[document_id] = document_vector

    def get_candidates(self, term_index):
        return self.inverted_index[term_index]

    def match(self, query, top_k, return_scores=False):
        candidates = set()

        for term_index in query.indices:
            candidates.update(self.get_candidates(term_index))

        scores = []
        candidates = list(candidates)
        for candidate in candidates:
            scores.append(self._relevance(query, candidate))

        if top_k:
            scores_arr = np.array(scores)
            print(f' scores_arr {scores_arr} and top_k {top_k}')
            top_indices = np.argpartition(scores_arr, top_k)
            top_candidates = operator.itemgetter(*top_indices.tolist())(candidates)
            top_scores = np.take_along_axis(scores_arr, top_indices, axis=0).tolist()
            if return_scores:
                return zip(top_scores, top_candidates)
            else:
                return top_candidates
        else:
            results = sorted(zip(scores, candidates), reverse=True)

            if return_scores:
                return results
            else:
                return [element for _, element in results]

    def _relevance(self, query_vec, candidate):
        candidate_vector = self.document_sparse_vectors[candidate]
        candidate_dense = np.array(candidate_vector.todense())[0]
        number_words = len(candidate_vector.indices)
        prod = 1
        for term_index in query_vec.indices:
            tf = self._tf(candidate_dense, term_index, number_words)
            idf = self._idf(term_index)
            prod = prod * tf * idf
        return prod

    def _tf(self, candidate_dense, term_idx, number_words):
        return candidate_dense[term_idx] / number_words

    def _idf(self, term_idx):
        return self.idfs.get(term_idx, 0)


class SimpleInvertedIndexer(Executor):
    """
    A simple inverted indexer that stores Document Lists in buckets given their sparse embedding input
    """

    @staticmethod
    def load_from_file(base_path):
        inverted_index_path = os.path.join(base_path, 'inverted_index.pickle')
        with open(inverted_index_path, 'rb') as f:
            return pickle.load(f)

    @staticmethod
    def store_to_file(base_path, inverted_idx):
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        inverted_index_path = os.path.join(base_path, 'inverted_index.pickle')
        with open(inverted_index_path, 'wb') as f:
            pickle.dump(inverted_idx, f)

    def __init__(
            self,
            inverted_index_file_name: str,
            # maybe better provide a link to a trained vectorizer
            corpus: List[str] = ['hello', 'he', 'she', 'ball', 'ski', 'sport', 'football'],
            default_traversal_paths: Tuple[str] = ['r'],
            default_top_k: int = 2,
            *args,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.vectorizer = CountVectorizer(stop_words='english')
        self.vectorizer.fit(corpus)
        self.inverted_index_file_name = inverted_index_file_name
        self.default_traversal_paths = default_traversal_paths
        self.default_top_k = default_top_k
        self.inverted_index = InvertedIndex()
        self.inverted_index_full_path = os.path.join(self.workspace, inverted_index_file_name)
        self._docs = DocumentArrayMemmap(self.workspace + f'/index_file_name')

        if os.path.exists(self.inverted_index_full_path):
            self.inverted_index = self.load_from_file(self.inverted_index_full_path)
        self.logger = get_logger(self)

    @requests(on='/index')
    def index(
            self,
            docs: Optional['DocumentArray'] = None,
            parameters: Optional[Dict] = {},
            **kwargs,
    ):
        """Add documents to the inverted index
        :param docs: the docs to add
        :param parameters: the parameters dictionary
        """
        if not docs:
            return
        traversal_paths = parameters.get(
            'traversal_paths', self.default_traversal_paths
        )
        flat_docs = docs.traverse_flat(traversal_paths)
        texts = flat_docs.get_attributes('text')
        embeddings = self.vectorizer.transform(texts).toarray()
        for doc, dense_embedding in zip(flat_docs, embeddings):
            sparse_embedding = csr_matrix(dense_embedding)
            self.inverted_index.add(doc.id, sparse_embedding)
            self._docs.append(doc)

    @requests(on='/search')
    def search(
            self,
            docs: Optional['DocumentArray'] = None,
            parameters: Optional[Dict] = {},
            **kwargs,
    ):
        """Retrieve results from the inverted index

        :param docs: the Documents to search with
        :param parameters: the parameters for the search"""
        if not docs:
            return
        if not self._docs:
            self.logger.warning(
                'no documents are indexed. searching empty docs. returning.'
            )
            return
        traversal_paths = parameters.get(
            'traversal_paths', self.default_traversal_paths
        )
        flat_docs = docs.traverse_flat(traversal_paths)
        texts = flat_docs.get_attributes('text')
        embeddings = self.vectorizer.transform(texts).toarray()
        top_k = int(parameters.get('top_k', self.default_top_k))
        for doc, embedding in zip(flat_docs, embeddings):
            sparse_embedding = csr_matrix(embedding)
            scores_matches = self.inverted_index.match(sparse_embedding, top_k, return_scores=True)
            for score, match_id in scores_matches:
                doc.matches.append(self._docs[match_id])
                doc.matches[-1].scores['tfidf'] = score

    @requests(on='/dump')
    def dump(
        self,
        **kwargs,
    ):
        self._dump()

    @requests(on='/cache_idfs')
    def cache_idfs(
        self,
        **kwargs,
    ):
        self.inverted_index.cache_idfs()

    def _dump(self):
        self.inverted_index.cache_idfs()
        self.store_to_file(self.inverted_index_full_path, self.inverted_index)

    def close(self):
        self._dump()
        super().close()
