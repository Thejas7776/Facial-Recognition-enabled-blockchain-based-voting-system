import hashlib
import json
from datetime import datetime

class Block:
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": str(self.timestamp),
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        print(f"Block Mined: {self.hash}")

class Blockchain:
    def __init__(self):
        self.chain = []
        self.difficulty = 4  # Adjust as needed
        self.create_genesis_block()

    def create_genesis_block(self):
        # Check if the chain is empty before creating a genesis block
        if not self.chain:
            genesis_block = Block(0, datetime.utcnow(), "Genesis Block", "0")
            genesis_block.mine_block(self.difficulty)
            self.chain.append(genesis_block)
            print("Genesis block created.")

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, new_block):
        new_block.previous_hash = self.last_block.hash
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        print(f"Block added: {new_block.hash}")

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False
        return True

# Initialize the blockchain (can be loaded from storage in a real app)
# For simplicity, we'll initialize an in-memory blockchain here.
# In a persistent application, you would load/save the chain from/to a database or file.
# blockchain = Blockchain() # This would be instantiated and managed by the Flask app context.
