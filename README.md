dqueue
======

dqueue is a distributed queue wrapper for [redis-py](https://github.com/andymccurdy/redis-py) package.

dqueue implements scenario of multiple users working simultaneously
with a pool of projects represented by ids. Each user can lock a
bunch of projects exclusively so that no other users can lock the same
ids for themselves until the lock is expired.

A real-world problem the dqueue solves is work of
adminstrators/moderators team processing projects: pushing them into
queue, locking, removing projects from the queue, etc, so that each
team member could work with his or her own portion from the pool of
all projects.

Example
======

```
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
```

Author
======

dqueue developed and maintained by Vitaly R. Samigullin.

License
=======

See LICENSE file.

