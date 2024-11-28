# SharedMemLib.py
from random import random
import threading
import socketserver
import sys
import time
import mmap
import os
import struct
from multiprocessing import shared_memory, Lock
from enum import Enum
class Mode(Enum):
    READ = 1
    WRITE = 2

mutex = Lock()
MEM_BLOCK_NAME1 = "shared_memory_block1"
MEM_BLOCK_NAME2 = "shared_memory_block2"
MEM_BLOCK_SIZE = 1024

class Mode(Enum):
    READ = 1
    WRITE = 2

# Function to read and write to shared memory
# mode: Mode.READ or Mode.WRITE
# toWrite: String to write to shared memory (only used in Mode.WRITE)
# Returns: String read from shared memory (only used in Mode.READ)
# Note: This function is thread-safe, so it should be called with a thread
def read_write_sharedMem(mode: Mode, toWrite: str = None, agentId: int = 0):
    MEM_BLOCK_NAME = MEM_BLOCK_NAME1 if agentId == 1 else MEM_BLOCK_NAME2
    mutex.acquire()
    try:
        shm_c = shared_memory.SharedMemory(MEM_BLOCK_NAME)
    except FileNotFoundError:
        shm_c = shared_memory.SharedMemory(create=True, size=MEM_BLOCK_SIZE, name=MEM_BLOCK_NAME)
    except FileExistsError:
        return None
        
    return_value = None
    #for i in range(1000):
    # Acquire the semaphore lock
    
    if mode == Mode.READ:
        read_bytes = bytearray()
        while True:
            chunk = bytes(shm_c.buf[:MEM_BLOCK_SIZE])
            read_bytes.extend(chunk)
            if b'\x00' in chunk:
                break
        read_str = read_bytes.rstrip(b'\x00').decode('utf-8')
        #print(read_str)  # Example action, adjust as needed
        return_value = read_str
        #break
    elif mode == Mode.WRITE and toWrite is not None:
        to_write_bytes = toWrite.encode('utf-8')
        for start in range(0, len(to_write_bytes), MEM_BLOCK_SIZE):
            end = start + MEM_BLOCK_SIZE
            chunk = to_write_bytes[start:end]
            bytes_to_write = bytearray(chunk)
            # Ensure the chunk is exactly MEM_BLOCK_SIZE bytes
            #TODO: Some chunks may be equal to MEM_BLOCK_SIZE, so it would not end the reading
            if len(bytes_to_write) < MEM_BLOCK_SIZE:
                bytes_to_write.extend(b'\x00' * (MEM_BLOCK_SIZE - len(bytes_to_write)))
            shm_c.buf[:MEM_BLOCK_SIZE] = bytes_to_write
        #break
    # Release the semaphore lock
    mutex.release()
    return return_value