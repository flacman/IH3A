import threading
import string
import random
import time

class Selector:
    def __init__(self, list1, list2, num_threads):
        self.users = list1
        self.passwords = list2
        self.num_threads = num_threads
        self.results = set()
        self.signal = threading.Event()
        self.lock = threading.Lock()
        self.indexUsrs = 0
        self.indexPass_map = {i: 0 for i in range(len(list1))}
        self.PasswordSpray = False
        self.total_pairs = len(list1) * len(list2)
        self.processed_pairs = 0

    def get_next_pair(self):
        with self.lock:
            while self.indexUsrs < len(self.users):
                    if(self.indexPass_map[self.indexUsrs] < len(self.passwords)):
                         break
                    self.indexUsrs += 1
                    if self.indexUsrs >= len(self.users):
                        self.indexUsrs = 0
            if(self.indexUsrs == len(self.users) or self.indexPass_map[self.indexUsrs] >= len(self.passwords)):
                return None, None
            if not self.PasswordSpray:
                item1 = self.users[self.indexUsrs]
                item2 = self.passwords[self.indexPass_map[self.indexUsrs]]
                self.indexPass_map[self.indexUsrs] += 1
                if self.indexPass_map[self.indexUsrs] >= len(self.passwords):
                    self.indexUsrs += 1
            else:
                item1 = self.users[self.indexUsrs]
                
                
                item2 = self.passwords[self.indexPass_map[self.indexUsrs]]

                if self.indexUsrs >= len(self.users):
                    self.indexUsrs = 0
                    self.indexPass_map[self.indexUsrs] += 1

            self.processed_pairs += 1
            return item1, item2

    def worker(self):
        while True:
            time.sleep(0.001)
            item1, item2 = self.get_next_pair()
            if item1 is None or item2 is None:
                break
            with self.lock:
                self.results.add((item1, item2))

    def start(self):
        threads = []
        for _ in range(self.num_threads):
            thread = threading.Thread(target=self.worker)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def change_traversal(self):
        with self.lock:
            self.PasswordSpray = not self.PasswordSpray
            #self.indexUsrs = 0

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def change_traversal_periodically(selector, interval, stop_event):
    while not stop_event.is_set():
        time.sleep(interval)
        selector.change_traversal()

def test_selector():
    list1 = [generate_random_string() for _ in range(500)]
    list2 = [generate_random_string() for _ in range(100)]
    
    selector = Selector(list1, list2, 4)
    
    stop_event = threading.Event()
    # Start a thread to change the traversal option every 5 seconds
    change_thread = threading.Thread(target=change_traversal_periodically, args=(selector, 5, stop_event))
    change_thread.start()
    
    selector.start()
    
    stop_event.set()
    change_thread.join()
    
    print(f"Results length after traversal: {len(selector.results)}")
    assert len(selector.results) == len(list1) * len(list2), "Traversal did not cover all combinations"

    # Ensure no duplicates

    assert len(selector.results) == len(list1) * len(list2), "There are duplicate pairs in the results"

if __name__ == "__main__":
    test_selector()