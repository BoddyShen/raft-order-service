from threading import Lock, RLock


catalogs = {
    "Tux": {"name": "Tux", "price": 6.9, "quantity": 100},
    "Uno": {"name": "Uno", "price": 5.0, "quantity": 100},
    "Clue": {"name": "Clue", "price": 15.0, "quantity": 100},
    "Lego": {"name": "Lego", "price": 23.3, "quantity": 100},
    "Chess": {"name": "Chess", "price": 17.5, "quantity": 100},
    "Barbie": {"name": "Barbie", "price": 10.0, "quantity": 100},
    "Bubbles": {"name": "Bubbles", "price": 2.75, "quantity": 100},
    "Frisbee": {"name": "Frisbee", "price": 8.8, "quantity": 100},
    "Twister": {"name": "Twister", "price": 13.3, "quantity": 100},
    "Elephant": {"name": "Elephant", "price": 20.0, "quantity": 100},
}


class ReadWriteLock:
    """
    A class implementing a read-write lock mechanism to allow concurrent read access
    for multiple threads but exclusive write access for a single thread.
    """

    def __init__(self):
        self.write_lock = Lock()  # Lock for managing write access
        self.read_lock = RLock()  # Reentrant lock for managing read access counters
        self.readers = 0  # Counter for active readers

    def acquire_read(self):
        """
        Acquire a read lock. Multiple readers can hold this type of lock simultaneously.
        """
        with self.read_lock:
            self.readers += 1
            # If this is the first reader, acquire the write lock
            if self.readers == 1:
                self.write_lock.acquire()

    def release_read(self):
        """
        Release a read lock.
        """
        with self.read_lock:
            self.readers -= 1
            # If there are no more readers, release the write lock
            if self.readers == 0:
                self.write_lock.release()

    def acquire_write(self):
        """
        Acquire a write lock. This method will block until there are no active readers,
        ensuring exclusive access for writing.
        """
        self.write_lock.acquire()

    def release_write(self):
        """
        Release a write lock.
        """
        self.write_lock.release()

    def __enter__(self):
        """
        Enter the context manager. Acquires the write lock.
        """
        self.acquire_write()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager. Releases the write lock.
        """
        self.release_write()