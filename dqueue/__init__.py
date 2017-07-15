import redis
import time

from typing import Any, Set, Iterable


class DistributedQueue(object):
    """
    Distributed queue wrapper for redis-py package

    DistributedQueue class implements scenario of multiple users
    working simultaneously with a pool of projects represented by ids.
    Each user can lock a bunch of projects exclusively so that no
    other users can lock the same ids for themselves until the lock is
    expired.

    A real-world problem the queue solves is work of
    adminstrators/moderators team processing projects (or other
    entities): pushing them into queue, locking, removing items from
    the queue, etc, so that each team member could work with his or
    her own portion from the pool of all projects.

    Example:

    $ docker run -p 6379:6379 redis
    $ python

    >>> import redis, dqueue
    >>> connection = redis.StrictRedis(host='localhost', port=6379, db=0)
    >>> queue = dqueue.DistributedQueue(connection=connection, ttl_seconds=60*20)
    >>> queue.lock_pids(user_id=1, pids=[1,2,3,4,5])
    {1, 2, 3, 4, 5}
    >>> queue.lock_pids(user_id=2, pids=[6,7,8])
    {6, 7, 8}
    >>> queue.retrieve_user(user_id=1)
    {1, 2, 3, 4, 5}
    >>> queue.retrieve_user(user_id=2)
    {6, 7, 8}
    >>> queue.retrieve_all()
    {1, 2, 3, 4, 5, 6, 7, 8}
    >>> queue.remove_pids(user_id=2, pids=[6,8])
    {6, 8}
    >>> queue.remove_all(user_id=1)
    {1, 2, 3, 4, 5}
    >>> queue.retrieve_all()
    {7}
    """

    def __init__(self,
                 connection: redis.client.StrictRedis,
                 ttl_seconds: int=600):
        self.redis = connection
        self.lock_ttl = ttl_seconds

        self.project_name = 'project'
        self.user_name = 'user'

    def _key(self, infix: str, id: Any) -> str:
        """
        Return string to be used in Redis as a key
        """
        return f'{self.project_name}:{infix}:{id}'

    def retrieve_all(self) -> Set[int]:
        """
        Return all unexpired locked project ids
        """
        # Get key pattern
        pattern = self._key(infix=self.user_name, id='*')

        # Scan for keys
        keys = self.redis.keys(pattern=pattern)

        # Union all values
        now = int(time.time())
        birth = now - self.lock_ttl
        dest = self._key(infix='temp', id=now)

        if keys:
            self.redis.zunionstore(dest=dest, keys=keys, aggregate='max')

            # Get only unexpired projects
            all_locked = self.redis.zrangebyscore(name=dest, min=birth, max=now)

            # Remove temporary zset
            self.redis.delete(dest)

            return {int(key) for key in all_locked}

        return set()

    def retrieve_user(self, user_id: int) -> Set[int]:
        """
        Return all unexpired projected from user's queue
        """
        now = int(time.time())
        birth = now - self.lock_ttl
        key = self._key(infix=self.user_name, id=user_id)

        # Get unexpired values
        pids = self.redis.zrangebyscore(name=key, min=birth, max=now)

        # Remove expired values from zset
        # Assume: min and max included,
        # so max score is creation timestamp minus 60 sec
        self.redis.zremrangebyscore(name=key, min='-inf', max=(birth - 60))

        return {int(key) for key in pids}

    def lock_pids(self, user_id: int, pids: Iterable[int]) -> Set[int]:
        """
        Lock project ids to user's queue, return ids that were locked
        """
        now = int(time.time())
        user_key = self._key(infix=self.user_name, id=user_id)

        # Add projects atomically
        pipe = self.redis.pipeline()

        # Set value if key's not set yet
        locked_pids = set()

        for pid in pids:
            pid_key = self._key(infix=self.project_name, id=pid)
            if pipe.setnx(pid_key, user_id):
                pipe.pexpire(pid_key, self.lock_ttl * 1000)  # ms
                pipe.zadd(user_key, now, str(pid))
                locked_pids.add(pid)
        pipe.execute()

        return locked_pids

    def remove_pid(self, user_id: int, pid: int) -> bool:
        """
        Remove single pid from user's queue

        Return True if removal succeeded, False otherwise.
        """
        pid = str(pid)

        pid_key = self._key(infix=self.project_name, id=pid)
        user_key = self._key(infix=self.user_name, id=user_id)
        pipe = self.redis.pipeline()

        def rm_transaction(pipe):
            val = pipe.get(pid_key)

            if val and int(val) == user_id:
                pipe.multi()
                result = pipe.delete(pid_key)
                if result:
                    pipe.zrem(user_key, pid)

        return self.redis.transaction(rm_transaction, pid_key)

    def remove_pids(self, user_id: int, pids: Iterable[int]) -> Set[int]:
        """
        Remove ids from user's queue atomically
        """
        removed_pids = set()

        for pid in pids:
            result = self.remove_pid(user_id, pid)

            if result:
                removed_pids.add(pid)

        return removed_pids

    def remove_all(self, user_id: int) -> Set[int]:
        """
        Remove all ids from user's queue
        """
        queue = self.retrieve_user(user_id=user_id)
        return self.remove_pids(user_id=user_id, pids=queue)
