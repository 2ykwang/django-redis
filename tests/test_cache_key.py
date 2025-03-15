import time
from typing import Any, Dict

import pytest
from redis import Redis
from redis.lock import Lock

from django_redis.cache import RedisCache
from django_redis.util import CacheKey, default_reverse_key


class TestDjangoRedisCache:

    @staticmethod
    def _generate_key(cache: RedisCache, key: str) -> str:
        """
        내부적으로 key 네임스페이싱이 어떻게 구성되는지 반환하는 헬퍼 메서드
        """
        return f"{cache.key_prefix}:{cache.version}:{key}"

    def test_make_key_in_redis_cache(self, cache: RedisCache):
        key = "mykey"

        generated_key = cache.client.make_key(key)
        expected_key = f"{cache.key_prefix}:{cache.version}:{key}"

        assert str(generated_key) == expected_key

    def test_cachekey_original_key(self, cache: RedisCache):
        key_str = f"{cache.key_prefix}:{cache.version}:mykey"
        ck = CacheKey(key_str)

        assert ck.original_key() == "mykey"

    def test_default_reverse_key(self, cache:RedisCache, redis_connection: Redis):
        key = "prefix:version:mykey"
        reverse_key = default_reverse_key(key)
        expected = "mykey"

        assert reverse_key == expected

    def test_make_key_with_custom_prefix_and_version(self, cache: RedisCache):
        key = "anotherkey"
        custom_prefix = "custom"
        custom_version = 10

        generated_key = cache.client.make_key(key,prefix=custom_prefix,version=custom_version)
        expected_key = f"{custom_prefix}:{custom_version}:{key}"

        assert str(generated_key) == expected_key

    def test_set_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "set_test_key_namespacing"
        expected_key = f"{cache.key_prefix}:{cache.version}:{key}"

        cache.set(key, "value")

        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
    
    
    def test_set_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "set_test_key_namespacing"
        expected_key = self._generate_key(cache, key)
        cache.set(key, "value")
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
    
    
    def test_delete_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "delete_test"
        expected_key = self._generate_key(cache, key)
        cache.set(key, "value")
        cache.delete(key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key not in stored_keys
    
    
    def test_delete_pattern_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key1 = "pattern_test1"
        key2 = "pattern_test2"
        expected_key1 = self._generate_key(cache, key1)
        expected_key2 = self._generate_key(cache, key2)
        cache.set(key1, "v1")
        cache.set(key2, "v2")
        # delete_pattern는 패턴에 매칭되는 모든 key를 삭제합니다.
        pattern = self._generate_key(cache, "pattern*")
        cache.delete_pattern(pattern)
        keys1 = [k.decode() for k in redis_connection.keys(expected_key1)]
        keys2 = [k.decode() for k in redis_connection.keys(expected_key2)]
        assert expected_key1 not in keys1
        assert expected_key2 not in keys2
    
    
    def test_delete_many_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        keys = ["dm_test1", "dm_test2", "dm_test3"]
        for key in keys:
            cache.set(key, "value")
        cache.delete_many(keys)
        for key in keys:
            expected_key = self._generate_key(cache, key)
            stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
            assert expected_key not in stored_keys
    
    
    def test_clear_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        cache.set("clear_test1", "v1")
        cache.set("clear_test2", "v2")
        cache.clear()
        pattern = self._generate_key(cache, "*")
        stored_keys = [k.decode() for k in redis_connection.keys(pattern)]
        assert len(stored_keys) == 0
    
    
    def test_get_many_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        keys_values = {"gm_test1": "v1", "gm_test2": "v2"}
        # DefaultClient.get_many는 여러 key의 값을 가져옵니다.
        # 내부적으로 make_key를 사용하여 key를 네임스페이싱합니다.
        cache.set_many(keys_values)
        result = cache.get_many(list(keys_values.keys()))
        for key, value in keys_values.items():
            expected_key = self._generate_key(cache, key)
            stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
            assert expected_key in stored_keys
            assert result.get(key) == value
    
    
    def test_set_many_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        keys_values = {"sm_test1": "v1", "sm_test2": "v2"}
        cache.set_many(keys_values)
        for key in keys_values:
            expected_key = self._generate_key(cache, key)
            stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
            assert expected_key in stored_keys
    
    
    def test_incr_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "incr_test"
        cache.set(key, 0)
        cache.incr(key)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert int(cache.get(key)) == 1
    
    
    def test_decr_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "decr_test"
        cache.set(key, 1)
        cache.decr(key)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert int(cache.get(key)) == 0
    
    
    def test_has_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "has_key_test"
        expected_key = self._generate_key(cache, key)
        cache.set(key, "exists")
        assert cache.has_key(key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        cache.delete(key)
        assert not cache.has_key(key)
    
    
    def test_keys_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "keys_test"
        expected_key = self._generate_key(cache, key)
        cache.set(key, "value")
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
    
    
    def test_iter_keys_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "iter_keys_test"
        expected_key = self._generate_key(cache, key)

        cache.set(key, "value")
        iter_keys = list(redis_connection.iter_keys(expected_key))

        assert expected_key in iter_keys
    
    
    def test_ttl_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "ttl_test"
        cache.set(key, "value")
        cache.expire(key, 10)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        ttl_value = cache.ttl(key)
        assert 0 < ttl_value <= 10
    
    
    def test_pttl_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "pttl_test"
        cache.set(key, "value")
        cache.pexpire(key, 5000)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        pttl_value = cache.pttl(key)
        assert 0 < pttl_value <= 5000
    
    
    def test_persist_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "persist_test"
        cache.set(key, "value")
        cache.expire(key, 10)
        cache.persist(key)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        # persist 후 ttl은 -1로 반환됩니다.
        assert cache.ttl(key) == -1
    
    
    def test_expire_at_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        import time
        key = "expire_at_test"
        cache.set(key, "value")
        expire_time = int(time.time()) + 5
        cache.expire_at(key, expire_time)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        ttl_value = cache.ttl(key)
        assert 0 < ttl_value <= 5
    
    
    def test_pexpire_at_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        import time
        key = "pexpire_at_test"
        cache.set(key, "value")
        expire_at_ms = int(time.time() * 1000) + 5000
        cache.pexpire_at(key, expire_at_ms)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        pttl_value = cache.pttl(key)
        assert 0 < pttl_value <= 5000
    
    
    def test_lock_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "lock_test"
        lock = cache.lock(key, timeout=5)
        acquired = lock.acquire(blocking=False)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        if acquired:
            lock.release()
    
    
    def test_touch_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        import time
        key = "touch_test"
        cache.set(key, "value")
        cache.expire(key, 10)
        original_ttl = cache.ttl(key)
        time.sleep(1)
        cache.touch(key)
        new_ttl = cache.ttl(key)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert new_ttl > original_ttl - 1
    
    
    def test_hset_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        # hset은 hash 이름과 key를 구분합니다.
        key = "hset_test_key"
        field = "f1"
        expected_key = self._generate_key(cache, key)

        cache.hset(key, field, "value1")
        assert redis_connection.hexists(expected_key, field)
    
    
    def test_hdel_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "hdel_test_key"
        field = "f1"
        expected_key = self._generate_key(cache, key)

        cache.hset(key, field, "value1")
        assert redis_connection.hexists(expected_key, field)

        cache.hdel(key, field)
        assert not redis_connection.hexists(expected_key, field)

    
    def test_hlen_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "hlen_test_hash"
        field1 = "f1"
        field2 = "f2"
        expected_key = self._generate_key(cache, key)

        cache.hset(key, field1, "v1")
        cache.hset(key, field2, "v2")

        assert redis_connection.hlen(expected_key) == 2

    
    
    def test_hkeys_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "hkeys_test_hash"
        field1 = "f1"
        field2 = "f2"
        expected_key = self._generate_key(cache, key)

        cache.hset(key, field1, "v1")
        cache.hset(key, field2, "v2")

        keys = redis_connection.hkeys(expected_key)

        expected_fields = [k.decode() if isinstance(k, bytes) else k for k in keys]

        assert [field1, field2] == expected_fields
    
    def test_hexists_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        hash_name = "hexists_test_hash"
        key = "f1"
        cache.hset(hash_name, key, "v1")
        exists = cache.hexists(hash_name, key)
        expected_key = self._generate_key(cache, key)
        # hkeys를 통해 저장된 field key 확인
        stored_fields = [k.decode() for k in cache.hkeys(hash_name)]

        assert expected_key in stored_fields
        assert exists
    
    
    def test_sadd_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "sadd_test"
        cache.sadd(key, "member1")
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
    
    
    def test_scard_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "scard_test"
        cache.sadd(key, "member1", "member2")
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert cache.scard(key) == 2
    
    
    def test_sdiff_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key1 = "sdiff_test1"
        key2 = "sdiff_test2"
        cache.sadd(key1, "a", "b", "c")
        cache.sadd(key2, "b", "c", "d")
        expected_key1 = self._generate_key(cache, key1)
        expected_key2 = self._generate_key(cache, key2)
        keys1 = [k.decode() for k in redis_connection.keys(expected_key1)]
        keys2 = [k.decode() for k in redis_connection.keys(expected_key2)]
        assert expected_key1 in keys1
        assert expected_key2 in keys2
        diff = cache.sdiff(key1, key2)
        assert "a" in diff
    
    
    def test_sdiffstore_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        src = "sdiffstore_test_src"
        dest = "sdiffstore_test_dest"
        cache.sadd(src, "a", "b", "c")
        cache.sdiffstore(dest, src, "b", "c", "d")
        expected_dest = self._generate_key(cache, dest)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_dest)]
        assert expected_dest in stored_keys
    
    
    def test_sinter_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key1 = "sinter_test1"
        key2 = "sinter_test2"
        cache.sadd(key1, "a", "b")
        cache.sadd(key2, "b", "c")
        expected_key1 = self._generate_key(cache, key1)
        expected_key2 = self._generate_key(cache, key2)
        keys1 = [k.decode() for k in redis_connection.keys(expected_key1)]
        keys2 = [k.decode() for k in redis_connection.keys(expected_key2)]
        assert expected_key1 in keys1
        assert expected_key2 in keys2
        inter = cache.sinter(key1, key2)
        assert "b" in inter
    
    
    def test_sinterstore_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        src1 = "sinterstore_test1"
        src2 = "sinterstore_test2"
        dest = "sinterstore_test_dest"
        cache.sadd(src1, "a", "b")
        cache.sadd(src2, "b", "c")
        cache.sinterstore(dest, src1, src2)
        expected_dest = self._generate_key(cache, dest)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_dest)]
        assert expected_dest in stored_keys
    
    
    def test_smismember_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "smismember_test"
        cache.sadd(key, "member1", "member2")
        result = cache.smismember(key, ["member1", "member3"])
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert result.get("member1") is True
        assert result.get("member3") is False
    
    
    def test_sismember_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "sismember_test"
        cache.sadd(key, "member1")
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert cache.sismember(key, "member1")
    
    
    def test_smembers_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "smembers_test"
        cache.sadd(key, "member1", "member2")
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        members = cache.smembers(key)
        assert "member1" in members
        assert "member2" in members
    
    
    def test_smove_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        src = "smove_test_src"
        dest = "smove_test_dest"
        cache.sadd(src, "member1")
        cache.smove(src, dest, "member1")
        expected_src = self._generate_key(cache, src)
        expected_dest = self._generate_key(cache, dest)
        src_keys = [k.decode() for k in redis_connection.keys(expected_src)]
        dest_keys = [k.decode() for k in redis_connection.keys(expected_dest)]
        assert expected_src in src_keys
        assert expected_dest in dest_keys
        assert not cache.sismember(src, "member1")
        assert cache.sismember(dest, "member1")
    
    
    def test_spop_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "spop_test"
        cache.sadd(key, "member1", "member2")
        _ = cache.spop(key)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        # spop 후 남은 멤버 수 검사
        assert cache.scard(key) == 1
    
    
    def test_srandmember_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "srandmember_test"
        cache.sadd(key, "member1", "member2")
        member = cache.srandmember(key)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert member in ("member1", "member2")
    
    
    def test_srem_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "srem_test"
        cache.sadd(key, "member1", "member2")
        cache.srem(key, "member1")
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert not cache.sismember(key, "member1")
    
    
    def test_sscan_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "sscan_test"
        members = [f"m{i}" for i in range(5)]
        cache.sadd(key, *members)
        cursor, result = cache.sscan(key, count=10)
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        assert isinstance(cursor, int)
        assert isinstance(result, set)  # sscan() 반환값은 set입니다.
    
    
    def test_sscan_iter_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key = "sscan_iter_test"
        members = [f"m{i}" for i in range(5)]
        cache.sadd(key, *members)
        iter_result = list(cache.sscan_iter(key))
        expected_key = self._generate_key(cache, key)
        stored_keys = [k.decode() for k in redis_connection.keys(expected_key)]
        assert expected_key in stored_keys
        for m in members:
            assert m in iter_result
    
    
    def test_sunion_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        key1 = "sunion_test1"
        key2 = "sunion_test2"
        cache.sadd(key1, "a", "b")
        cache.sadd(key2, "b", "c")
        union_result = cache.sunion(key1, key2)
        expected_key1 = self._generate_key(cache, key1)
        expected_key2 = self._generate_key(cache, key2)
        keys1 = [k.decode() for k in redis_connection.keys(expected_key1)]
        keys2 = [k.decode() for k in redis_connection.keys(expected_key2)]
        assert expected_key1 in keys1
        assert expected_key2 in keys2
        for m in ("a", "b", "c"):
            assert m in union_result
    
    
    def test_sunionstore_key_namespacing(self, cache: RedisCache, redis_connection: Redis):
        src1 = "sunionstore_test1"
        src2 = "sunionstore_test2"
        dest = "sunionstore_test_dest"

        cache.sadd(src1, "a", "b")
        cache.sadd(src2, "b", "c")
        cache.sunionstore(dest, src1, src2)

        expected_dest = self._generate_key(cache, dest)

        stored_keys = [k.decode() for k in redis_connection.keys(expected_dest)]
        assert expected_dest in stored_keys

"""
	•	set O
	•	incr_version
	•	add O 
	•	get
	•	delete
	•	delete_pattern
	•	delete_many
	•	clear
	•	get_many
	•	set_many
	•	incr
	•	decr
	•	has_key
	•	keys
	•	iter_keys
	•	ttl
	•	pttl
	•	persist
	•	expire
	•	expire_at
	•	pexpire
	•	pexpire_at
	•	lock
	•	close
	•	touch
	•	sadd
	•	scard
	•	sdiff
	•	sdiffstore
	•	sinter
	•	sinterstore
	•	sismember
	•	smembers
	•	smove
	•	spop
	•	srandmember
	•	srem
	•	sscan
	•	sscan_iter
	•	smismember
	•	sunion
	•	sunionstore
	•	hset
	•	hdel
	•	hlen
	•	hkeys
	•	hexists
"""