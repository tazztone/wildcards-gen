
from typing import Optional, Any, Protocol, Tuple
from tqdm import tqdm as _tqdm

class ProgressCallback(Protocol):
    """Protocol for progress reporting."""
    def __call__(self, progress: float | Tuple[int, int], desc: Optional[str] = None) -> None:
        ...

class TqdmProgress:
    """Wrapper that adapts tqdm to the ProgressCallback protocol."""
    def __init__(self, total: Optional[int] = None, desc: str = "", unit: str = "it"):
        self.pbar = _tqdm(total=total, desc=desc, unit=unit)
    
    def __call__(self, progress: float | Tuple[int, int], desc: Optional[str] = None) -> None:
        """
        Update progress.
        If progress is float (0.0-1.0), we can't easily set tqdm unless we track total.
        If progress is (current, total), we can update pbar.
        """
        if desc:
            self.pbar.set_description(desc)
            
        if isinstance(progress, tuple):
            current, total = progress
            if self.pbar.total != total:
                self.pbar.total = total
                self.pbar.refresh()
            update_amt = current - self.pbar.n
            if update_amt > 0:
                self.pbar.update(update_amt)
        elif isinstance(progress, (int, float)):
            # Heuristic: if progress is float < 1.0, maybe it's percentage?
            # Tqdm is hard to drive with pure percentage unless manual.
            # We'll just update by 1 if it's an int increment, or ignore float for now if no total.
            if isinstance(progress, int) and progress > 1: # Absolute value?
                 # Assume this is 'n'
                 update_amt = progress - self.pbar.n
                 if update_amt > 0: self.pbar.update(update_amt)
            pass

    def close(self):
        self.pbar.close()

class NullProgress:
    """No-op progress."""
    def __call__(self, *args, **kwargs):
        pass
