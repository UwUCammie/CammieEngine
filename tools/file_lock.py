"""The exclusive flock subset used by local build and import tools."""

import os

if os.name != 'nt':
    from fcntl import LOCK_EX, LOCK_NB, LOCK_UN, flock
else:
    import msvcrt
    import time

    LOCK_EX = 2
    LOCK_NB = 4
    LOCK_UN = 8

    def flock(file, operation):
        descriptor = file if isinstance(file, int) else file.fileno()
        position = os.lseek(descriptor, 0, os.SEEK_CUR)
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            if operation == LOCK_UN:
                try:
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                except OSError as error:
                    # POSIX flock permits unlocking a descriptor which never
                    # acquired the lock; transaction cleanup depends on it.
                    if error.errno != 13:
                        raise
                return
            if operation not in (LOCK_EX, LOCK_EX | LOCK_NB):
                raise ValueError('Only exclusive locks and unlocks are supported')
            while True:
                try:
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    return
                except OSError as error:
                    if error.errno not in (13, 36):
                        raise
                    if operation & LOCK_NB:
                        raise BlockingIOError(error.errno, 'File is already locked') from error
                    time.sleep(0.1)
        finally:
            os.lseek(descriptor, position, os.SEEK_SET)
