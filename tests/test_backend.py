import datetime
import threading
import time
from datetime import timedelta
from typing import Iterable, List, Union, cast
from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.test import override_settings
from pytest_mock import MockerFixture

from django_redis.cache import RedisCache
from django_redis.client import ShardClient, herd
from django_redis.serializers.json import JSONSerializer
from django_redis.serializers.msgpack import MSGPackSerializer
from tests.settings_wrapper import SettingsWrapper


@pytest.fixture
def patch_itersize_setting() -> Iterable[None]:
    # destroy cache to force recreation with overriden settings
    del caches["default"]
    with override_settings(DJANGO_REDIS_SCAN_ITERSIZE=30):
        yield
    # destroy cache to force recreation with original settings
    del caches["default"]


class TestDjangoRedisCache:
    def test_setnx(self, cache: RedisCache):
        # we should ensure there is no test_key_nx in redis
        cache.delete("test_key_nx")
        res = cache.get("test_key_nx")
        assert res is None

        res = cache.set("test_key_nx", 1, nx=True)
        assert bool(res) is True
        # test that second set will have
        res = cache.set("test_key_nx", 2, nx=True)
        assert res is False
        res = cache.get("test_key_nx")
        assert res == 1

        cache.delete("test_key_nx")
        res = cache.get("test_key_nx")
        assert res is None

    def test_clear(self, cache: RedisCache):
        cache.set("foo", "bar")
        value_from_cache = cache.get("foo")
        assert value_from_cache == "bar"
        cache.clear()
        value_from_cache_after_clear = cache.get("foo")
        assert value_from_cache_after_clear is None

    def test_hset(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")
        cache.hset("foo_hash1", "foo1", "bar1")
        cache.hset("foo_hash1", "foo2", "bar2")
        assert cache.hlen("foo_hash1") == 2
        assert cache.hexists("foo_hash1", "foo1")
        assert cache.hexists("foo_hash1", "foo2")
        cache.hset("foo_hash1", mapping={"foo3": "bar3", "foo4": "bar4"})
        assert cache.hlen("foo_hash1") == 4
        assert cache.hexists("foo_hash1", "foo3")
        assert cache.hexists("foo_hash1", "foo4")

    def test_hget(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")

        cache.hset("foo_hash1", "foo1", "bar1")
        assert cache.hget("foo_hash1", "foo1") == "bar1"
        cache.hset("foo_hash1", mapping={"foo2": "bar2", "foo3": "bar3"})
        assert cache.hget("foo_hash1", "foo2") == "bar2"
        assert cache.hget("foo_hash1", "foo3") == "bar3"

    def test_hmget(self, cache: RedisCache):
        cache.hset("test_hash", mapping={"field1": "val1", "field2": "val2"})
        res = cache.hmget("test_hash", ["field1", "field2", "field3"])
        assert res == ["val1", "val2", None]

    
    def test_hincrby(self,cache: RedisCache): 
        cache.hset("test_hash", "counter", 10)
        # hincrby: 값 증가 후 반환값 확인
        new_val = cache.hincrby("test_hash", "counter", 5)
        assert new_val == 15

    def test_hincrbyfloat(self,cache: RedisCache): 
        cache.hset("test_hash", "float_val", 1.0)
        # hincrbyfloat: 부동 소수점 연산 결과 확인
        new_val = cache.hincrbyfloat("test_hash", "float_val", 0.5)
        assert abs(new_val - 1.5) < 1e-6

    def test_hsetnx(self,cache: RedisCache): 
        # hsetnx: 필드가 없을 때만 설정
        res = cache.hsetnx("test_hash", "field1", "value1")
        assert res is True
        # 이미 존재하는 필드에 대해 재설정 시도하면 False
        res = cache.hsetnx("test_hash", "field1", "value2")
        assert res is False
        val = cache.hget("test_hash", "field1")
        assert val == "value1"

    def test_hgetall(self,cache: RedisCache): 
        mapping = {"field1": "val1", "field2": "val2"}
        cache.hset("test_hash", mapping=mapping)
        # hgetall: 전체 hash 내용을 dict로 반환
        all_data = cache.hgetall("test_hash")
        assert all_data == mapping

    def test_hkeys(self,cache: RedisCache): 
        mapping = {"field1": "val1", "field2": "val2"}
        cache.hset("test_hash", mapping=mapping)
        # hkeys: 모든 필드(key) 목록 반환
        keys = cache.hkeys("test_hash")
        assert set(keys) == {"field1", "field2"}

    def test_hlen(self,cache: RedisCache): 
        mapping = {"field1": "val1", "field2": "val2"}
        cache.hset("test_hash", mapping=mapping)
        # hlen: 필드 수 반환
        length = cache.hlen("test_hash")
        assert length == 2

    def test_hscan(self,cache: RedisCache): 
        mapping = {f"field{i}": f"value{i}" for i in range(5)}
        cache.hset("test_hash", mapping=mapping)
        # hscan: 커서와 data dict 반환
        cursor, data = cache.hscan("test_hash")
        assert isinstance(cursor, int)
        # 반환된 데이터에 모든 필드가 포함되어야 함
        assert set(data.keys()) == set(mapping.keys())
        for key, value in mapping.items():
            assert data[key] == value

    def test_hdel(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")
        cache.hset("foo_hash2", "foo1", "bar1")
        cache.hset("foo_hash2", "foo2", "bar2")
        assert cache.hlen("foo_hash2") == 2
        deleted_count = cache.hdel("foo_hash2", "foo1")
        assert deleted_count == 1
        assert cache.hlen("foo_hash2") == 1
        assert not cache.hexists("foo_hash2", "foo1")
        assert cache.hexists("foo_hash2", "foo2")

    def test_hlen(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")
        assert cache.hlen("foo_hash3") == 0
        cache.hset("foo_hash3", "foo1", "bar1")
        assert cache.hlen("foo_hash3") == 1
        cache.hset("foo_hash3", "foo2", "bar2")
        assert cache.hlen("foo_hash3") == 2

    def test_hkeys(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")
        cache.hset("foo_hash4", "foo1", "bar1")
        cache.hset("foo_hash4", "foo2", "bar2")
        cache.hset("foo_hash4", "foo3", "bar3")
        keys = cache.hkeys("foo_hash4")
        assert len(keys) == 3
        for i in range(len(keys)):
            assert keys[i] == f"foo{i + 1}"

    def test_hexists(self, cache: RedisCache):
        if isinstance(cache.client, ShardClient):
            pytest.skip("ShardClient doesn't support get_client")
        cache.hset("foo_hash5", "foo1", "bar1")
        assert cache.hexists("foo_hash5", "foo1")
        assert not cache.hexists("foo_hash5", "foo")
