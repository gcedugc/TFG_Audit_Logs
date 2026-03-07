import hashlib


class MerkleTree:
    """Implementación de Árbol de Merkle usando SHA-256."""

    def __init__(self, leaves):
        self.leaves = [self._hash(leaf) for leaf in leaves]
        self.tree = []
        self._build()

    def _hash(self, data):
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def _hash_pair(self, a, b):
        return hashlib.sha256((a + b).encode('utf-8')).hexdigest()

    def _build(self):
        level = self.leaves
        self.tree.append(level)
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    next_level.append(self._hash_pair(level[i], level[i + 1]))
                else:
                    next_level.append(level[i])
            level = next_level
            self.tree.append(level)

    def get_root(self):
        return self.tree[-1][0] if self.tree else ""
