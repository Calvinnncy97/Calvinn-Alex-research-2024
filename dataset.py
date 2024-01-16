import torch
import os
import shutil
from torch.utils.data import IterableDataset, get_worker_info
import numpy as np
from typing import List, Any
from pathlib import Path
import struct
import random
import threading
import string
import pickle
from time import sleep

# Dtype to code mapping
dtypes = {1: np.uint8, 2: np.int8, 3: np.int16, 4: np.int32, 5: np.int64, 6: np.float32, 7: np.float64, 8: np.uint16}

# Function to map dtype to code
def code(dtype):
    for k in dtypes:
        if dtypes[k] == dtype:
            return k
    raise ValueError(dtype)


class MMappedDataset (IterableDataset):
    def __init__(self, 
                 block_size: int,
                 folder: str = None , 
                 filenames: List[str] = None, 
                 cache_size: int = 0, 
                 cache_size_on_disk: int = 0, 
                 disk_cache_dir: str ='',
                 shuffle: bool = True,
                 seed: int = 12345,
                 pad_token: Any = None,
                 file_open_limit: int = 10,
                 wrap: bool = False):
        
        # Assert that either folder or filenames must be defined
        assert folder is not None or filenames is not None
        
        # Assert that if cache_size_on_disk > 0, disk_cache_dir must be defined
        assert len(disk_cache_dir) > 0 if cache_size_on_disk> 0 else True
        
        self._block_size = block_size
        
        # Find files
        if filenames is None:
            folder = Path(folder)
            self._filenames = [str(path) for path in list(folder.rglob('*.bin'))]
        else:
            self._filenames = filenames
        
        # Set random seed
        self._shuffle = shuffle
        self._seed = seed
        random.seed(seed)
        if self._shuffle:
            random.shuffle(self._filenames)
        
        self._cache_size = cache_size
        self._cache_size_on_disk = cache_size_on_disk
        self._disk_cache_dir = disk_cache_dir
        if len(self._disk_cache_dir) > 0:
            os.makedirs(self._disk_cache_dir, exist_ok=True)
        
        self._pad_token = pad_token
        self._file_open_limit = file_open_limit
        self._wrap = wrap
        
    def __iter__(self):
        worker_info = get_worker_info()
        num_workers = worker_info.num_workers if worker_info is not None else 1
        worker_id = worker_info.id if worker_info is not None else 0
        
        # Split file paths equally among dataloader workers
        def split(filenames, n):
            k, m = divmod(len(filenames), n)
            return (filenames[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))
        
        split_filenames = list(split(self._filenames, num_workers))
        filenames = split_filenames[worker_id]
        
        return MMappedDatasetIterator(
            filenames=filenames,
            block_size=self._block_size,
            cache_size=self._cache_size,
            cache_size_on_disk=self._cache_size_on_disk, 
            disk_cache_dir=self._disk_cache_dir,
            shuffle=self._shuffle,
            seed=self._seed,
            pad_token=self._pad_token,
            file_open_limit=self._file_open_limit,
            wrap=self._wrap
        )


class MMappedDatasetIterator:
    def __init__(self, 
                 filenames, 
                 block_size, 
                 cache_size, 
                 cache_size_on_disk, 
                 disk_cache_dir, 
                 shuffle, 
                 seed, 
                 pad_token,
                 file_open_limit,
                 wrap) -> None:
        
        # Set random seed
        self._shuffle = shuffle
        self._rng_np = np.random.default_rng(seed)
        self._wrap = wrap
        
        self._filenames = filenames
        self._block_size = block_size
        self._pad_token = pad_token
        
        self._cache = []
        self._cache_size = cache_size
        
        self._disk_cache_paths = []
        self._cache_size_on_disk = cache_size_on_disk
        self._disk_cache_dir = disk_cache_dir
        
        self._file_open_limit = file_open_limit
        self._curr_file_id = 0
        self._file_dict = {}
        
        self._prefetch_data_thread = threading.Thread(target=self._prefetch_data)
        self._prefetch_data_thread.start()
        
    def _read_header(self, path):
        '''
        This method reads headers from the binary file.
        
        The header contains dtype and chunksize information.
        '''
        with open(path, "rb") as f:
            (dtype_code,) = struct.unpack("<B", f.read(1))
            dtype = dtypes[dtype_code]
            (chunk_size,) = struct.unpack("<Q", f.read(8))
        return dtype, chunk_size
    
    def _close_mmaps(self):
        '''
        This model closes opened file handlers
        '''
        for file in self._file_dict.values():
            file['mmap']._mmap.close()
    
    def _load_n_chunks(self):
        '''
        This function pre-open files for random sampling
        '''
        self._close_mmaps()
        file_dict = {}
        
        self._file_open_limit = min(self._file_open_limit, len(self._filenames[self._curr_file_id:]))
        
        if self._file_open_limit == 0:
            if self._wrap:
                self._curr_file_id = 0
            else:
                raise StopIteration

        for i in range(self._file_open_limit):
            filename = self._filenames[self._curr_file_id + i]
            
            file_dtype, file_chunk_size = self._read_header(filename)
            
            if file_chunk_size == 0:
                file_chunk_size = self._block_size
                
            mmap = np.memmap(filename, mode="r", order="C", offset=9, dtype=file_dtype)
            n_chunks = mmap.shape[0] // file_chunk_size
            n_blocks_per_chunk = (file_chunk_size // self._block_size) + 1 if (file_chunk_size % self._block_size) > 0 else (file_chunk_size // self._block_size)
            file_n_blocks = n_blocks_per_chunk * n_chunks
            file_dict[filename] = {
                'dtype' : file_dtype,
                'block_ids' : self._rng_np.permutation(file_n_blocks) if self._shuffle else range(file_n_blocks),
                'mmap' : mmap,
                'buffer' : memoryview(mmap)
            }

        self._curr_file_id += self._file_open_limit
        return file_dict
    
    def _generate_random_filename(self):
        '''
        This method generates a random file name
        '''
        random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
        filename = f"tmp_{random_string}.pkl"
        return os.path.join(self._disk_cache_dir, filename)
    
    def _sample_data(self):
        '''
        This method samples a random data from a random file
        '''
        if len(self._file_dict) == 0:
            self._file_dict = self._load_n_chunks()
        
        # Randomly select a file
        file_choices = list(self._file_dict.keys())
        file = random.choice(file_choices)
        
        # Randomly select a block from the file
        block_idx_index = random.choice(range(len(self._file_dict[file]['block_ids'])))
        block_idx = self._file_dict[file]['block_ids'][block_idx_index]
        
        # Remove the block after it is already sampled
        self._file_dict[file]['block_ids'] = np.delete(self._file_dict[file]['block_ids'], block_idx_index)
        
        # Remove files which all blocks have been sampled
        if len(self._file_dict[file]['block_ids']) == 0:
            self._file_dict.pop(file)
        
        # Get block from buffer
        elem_id = block_idx * self._block_size
        offset = np.dtype(dtype=self._file_dict[file]['dtype']).itemsize * elem_id
        data = np.frombuffer(self._file_dict[file]['buffer'], dtype=self._file_dict[file]['dtype'], count=self._block_size, offset=offset)
        
        # Pad tokens to max size if pad_token is defined
        if len(data) < self._block_size: 
            if self._pad_token is not None:
                data = data.copy()
                length = self._block_size - len(data)
                padding = np.full(length, self._pad_token)
                data = np.hstack((data, padding))
            else:
                print('WARNING: Token length does not equal to block size.')
                
        data = torch.from_numpy(data.astype(np.int64))
        return data
    
    def _prefetch_data(self):
        '''
        This method is a function which runs in the background to constantly fill up the cache
        '''
        while True:
            if len(self._cache) < self._cache_size:
                if len(self._disk_cache_paths) > 0:
                    pickle_filename = self._disk_cache_paths.pop(0)  # Replace with the actual filename
                    with open(pickle_filename, 'rb') as file:
                        cached_data = pickle.load(file)
                    self._cache.append(cached_data)
                    os.remove(pickle_filename)
                else:
                    self._cache.append(self._sample_data())
            else:
                if len(self._disk_cache_paths) < self._cache_size_on_disk:
                    data = self._sample_data()
                    filename = self._generate_random_filename()
                    self._disk_cache_paths.append(filename)
                    
                    with open(os.path.join(self._disk_cache_dir, filename), 'wb') as file:
                        pickle.dump(data, file) 
    
    # ----- CUSTOM FUNCTION TO GENERATE MASK -----
    def generate_masks(self, data, mask_prob=0.1):        
        #Example: Randomly masks any token with a probability of 0.1 for MLM
        
        mask_rand = torch.rand(data.size())
        masks = torch.ones(data.size())
        masks[mask_rand < mask_prob] = 0
        return masks
    # -----------------------------------------------
    
    def __del__(self):
        '''
        This method closes files, join threads and delete variable when the class is deleted
        '''
        self._close_mmaps()
        del self._file_dict
        self._prefetch_data_thread.join()
    
    def __next__(self):
        '''
        This method returns the next data when called
        '''
        # Waits for the thread to fill the cache in the first iteraton
        while len(self._cache) == 0:
            sleep(0.5)
        
        data = self._cache.pop(0)
        masks = self.generate_masks(data)
        
        return data, masks
    
    def __iter__(self):
        return self
        
    
class CombinedDataset(IterableDataset):
    def __init__(self, 
                 datasets: MMappedDataset, 
                 seed: int = 12345, 
                 weights: List = None):
        self._seed = seed
        self._datasets = datasets
        self._weights = weights
        n_datasets = len(datasets)
        if weights is None:
            self._weights = [1 / n_datasets] * n_datasets

    def __iter__(self):
        '''
        This method iterates on the next datasets based on probability weights
        '''
        return CombinedDatasetIterator(self._datasets, self._seed, self._weights)


class CombinedDatasetIterator:
    def __init__(self, datasets, seed, weights):
        self._datasets = [iter(el) for el in datasets]
        self._weights = weights
        self._rng = random.Random(seed)

    def __next__(self):
        '''
        This method iterates on the next datasets based on probability weights
        '''
        (dataset,) = self._rng.choices(self._datasets, weights=self._weights, k=1)
        return next(dataset)